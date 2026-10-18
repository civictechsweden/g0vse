import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from services.chains.export import publish_json
from services.press_images import export as press_export
from services.press_images.fetcher import fetch_listing
from services.press_images.parser import (
    LISTING,
    PressImageError,
    listing_root,
    parse_detail,
    parse_fragment,
)

pytestmark = pytest.mark.smoke
FIXTURES = Path(__file__).parent / "fixtures/press_images"
SOURCE = "/pressbilder/ulf-kristersson2/"


class PortraitDownloader:
    def __init__(self):
        self.b = self
        self.listing = (FIXTURES / "listing.html").read_text()
        self.response = json.loads((FIXTURES / "response.json").read_text())
        self.detail = (FIXTURES / "portrait.html").read_text()
        self.calls, self.pages = [], []

    def get_json(self, url):
        query = parse_qs(urlsplit(url).query)
        assert query["filterType"] == ["Structure"]
        assert query["filterByType"] == ["PressImagePage"]
        assert query["rootPageReference"] == ["108"]
        assert query["page"] == ["1"]
        self.calls.append(url)
        return deepcopy(self.response)

    def get_webpage(self, url):
        self.pages.append(url)
        if url == LISTING:
            return self.listing
        if url == SOURCE:
            return self.detail
        return None


def test_listing_keeps_multiple_portraits_per_person_and_absolute_assets():
    downloader = PortraitDownloader()
    records, labels = fetch_listing(downloader)
    assert len(downloader.calls) == 2
    assert len(records) == len({row["url"] for row in records}) == 3
    assert sum(row["name"] == "Johan Britz" for row in records) == 2
    row = next(row for row in records if row["url"] == SOURCE)
    assert row["department"] == "Statsrådsberedningen"
    assert row["role"] == "Statsminister"
    assert row["thumbnail"].startswith("https://www.regeringen.se/globalassets/")
    assert row["alt"]
    assert labels["2608"] == "Andreas Carlson"


def test_detail_preserves_original_image_credit_rights_and_markdown():
    downloader = PortraitDownloader()
    row = next(r for r in parse_fragment(downloader.response) if r["url"] == SOURCE)
    details, labels, markdown = parse_detail(downloader.detail, row)
    assert details["image"].endswith("/ulf-kristersson.jpg")
    assert "Ninni Andersson/Regeringskansliet" in details["credit"]
    assert "oktober 2022" in details["caption"]
    assert "inte användas kommersiellt" in details["rights"]
    assert details["published"] == "2022-10-19"
    assert "updated" not in details
    assert labels["2605"] == "Ulf Kristersson"
    assert markdown.startswith("# Ulf Kristersson\n")
    assert "Statsrådsberedningen" in markdown
    assert details["credit"] in markdown
    assert "inte användas kommersiellt" in markdown
    assert details["image"] in markdown
    assert "Dela" not in markdown


@pytest.mark.parametrize(
    "failure",
    ["partial", "duplicate", "invalid_url", "empty", "fallback", "missing_department"],
)
def test_invalid_or_partial_lists_are_rejected(failure):
    response = PortraitDownloader().response
    if failure == "partial":
        response["TotalCount"] += 1
    elif failure == "duplicate":
        response["TotalCount"] *= 2
        response["Message"] *= 2
    elif failure == "invalid_url":
        response["Message"] = response["Message"].replace(
            SOURCE, "/pressbilder/../outside/"
        )
    elif failure == "empty":
        response = {"TotalCount": 0, "Message": ""}
    elif failure == "fallback":
        response["Message"] = '<div class="sortcompact">ordinary page fallback</div>'
    else:
        response["Message"] = response["Message"].replace(
            "press__department-header", "other"
        )
    with pytest.raises(PressImageError):
        parse_fragment(response)


def test_duplicate_root_widgets_are_allowed_but_different_roots_are_rejected():
    html = PortraitDownloader().listing
    assert listing_root(html * 2)[0] == "108"
    with pytest.raises(PressImageError):
        listing_root(html + html.replace('data-rootpage="108"', 'data-rootpage="109"'))


@pytest.mark.parametrize("failure", ["network", "root", "partial", "changed"])
def test_failed_list_refresh_keeps_previous_export_codes_and_markdown(
    failure, monkeypatch, tmp_path
):
    downloader = PortraitDownloader()
    if failure == "root":
        downloader.listing = "<h1>Startsidan</h1>"
    elif failure == "partial":
        downloader.response["TotalCount"] += 1
    else:
        original = downloader.get_json

        def respond(url):
            if failure == "network":
                raise OSError("Disconnected")
            response = original(url)
            if len(downloader.calls) == 2:
                response["Message"] = response["Message"].replace(
                    "Statsminister", "Changed role"
                )
            return response

        monkeypatch.setattr(downloader, "get_json", respond)
    old = tmp_path / "api/pressbilder.json"
    old.parent.mkdir()
    old.write_text("[]\n")
    files, codes = {}, {"existing": "Existing code"}
    assert (
        press_export.prepare_press_image_export(downloader, codes, files, tmp_path)
        is None
    )
    publish_json(files, tmp_path)
    assert old.read_text() == "[]\n" and codes == {"existing": "Existing code"}
    assert not list(tmp_path.rglob("*.md"))


def test_successful_export_keeps_failed_details_and_does_not_rewrite_unchanged_md(
    monkeypatch, tmp_path
):
    downloader = PortraitDownloader()
    files, codes = {}, {}
    records = press_export.prepare_press_image_export(
        downloader, codes, files, tmp_path
    )
    assert len(records) == 3
    assert codes["2605"] == "Ulf Kristersson"
    assert codes["1293"] == "Statsrådsberedningen"
    publish_json(files, tmp_path)
    original = (tmp_path / (SOURCE.strip("/") + ".md")).read_bytes()
    assert b"Ninni Andersson" in original

    def unexpected_write(*args):
        raise AssertionError("Unchanged Markdown should not be rewritten")

    monkeypatch.setattr(press_export.Writer, "write_md", unexpected_write)
    assert (
        press_export.prepare_press_image_export(downloader, codes, {}, tmp_path)
        == records
    )
    downloader.detail = ""
    assert (
        press_export.prepare_press_image_export(downloader, codes, {}, tmp_path)
        == records
    )
    assert (tmp_path / (SOURCE.strip("/") + ".md")).read_bytes() == original
    # New unavailable portraits retain usable list data, not invented credits.
    listing_only = next(r for r in records if r["name"] == "Johan Britz")
    assert "credit" not in listing_only and "image" not in listing_only
    assert (tmp_path / (listing_only["url"].strip("/") + ".md")).exists()


def test_detail_identity_uses_url_even_when_two_portraits_have_the_same_name():
    downloader = PortraitDownloader()
    row = next(r for r in parse_fragment(downloader.response) if r["url"] == SOURCE)
    html = downloader.detail.replace(
        'content="https://www.regeringen.se/pressbilder/ulf-kristersson2/"',
        'content="https://www.regeringen.se/pressbilder/other-portrait/"',
    )
    with pytest.raises(PressImageError, match="URL disagrees"):
        parse_detail(html, row)
    with pytest.raises(PressImageError):
        parse_detail("<main><h1>Ulf Kristersson</h1></main>", row)


def test_missing_markdown_can_be_rebuilt_from_saved_credit_and_rights(tmp_path):
    downloader = PortraitDownloader()
    files, codes = {}, {}
    records = press_export.prepare_press_image_export(
        downloader, codes, files, tmp_path
    )
    publish_json(files, tmp_path)
    path = tmp_path / (SOURCE.strip("/") + ".md")
    path.unlink()
    downloader.detail = ""
    result = press_export.prepare_press_image_export(downloader, codes, {}, tmp_path)
    assert result == records
    markdown = path.read_text()
    assert "Ninni Andersson" in markdown
    assert "inte användas kommersiellt" in markdown
    assert "Ladda ner bilden" in markdown
