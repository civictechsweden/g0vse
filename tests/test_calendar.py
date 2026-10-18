import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from services.calendar import export as calendar_export
from services.calendar.fetcher import fetch_listing, refresh_details
from services.calendar.parser import CalendarError, parse_detail, parse_fragment
from services.chains.export import publish_json

pytestmark = pytest.mark.smoke
FIXTURES = Path(__file__).parent / "fixtures/calendar"
OLDEST = "/kalendarium/2023/01/utrikes-resa-bryssel/"
LATEST = "/kalendarium/2026/10/deltar-vid-invigningen-av-ireland-house/"


class CalendarDownloader:
    def __init__(self):
        self.b = self
        self.responses = {
            page: json.loads((FIXTURES / f"page-{page}.json").read_text())
            for page in (1, 2)
        }
        self.details = {
            OLDEST: (FIXTURES / "oldest.html").read_text(),
            LATEST: (FIXTURES / "latest.html").read_text(),
        }
        self.calls, self.pages = [], []

    def get_json(self, url):
        query = parse_qs(urlsplit(url).query)
        assert query["filterByType"] == ["CalendarEventPage"]
        assert query["filterFromToday"] == ["False"]
        assert query["pageSize"] == ["2"]
        page = int(query["page"][0])
        self.calls.append(page)
        return deepcopy(self.responses[page])

    def get_webpage(self, url):
        self.pages.append(url)
        return self.details.get(url)


def test_calendar_listing_preserves_dates_ranges_and_participant_codes():
    downloader = CalendarDownloader()
    rows, labels = fetch_listing(downloader, page_size=2)
    assert downloader.calls == [1, 2, 1]
    assert len(rows) == 3
    assert rows[0]["url"] == LATEST
    assert rows[0]["participants"] == ["2425", "2626"]
    assert rows[-1]["start_date"] == "2023-01-23"
    assert rows[1]["end_date"] == "2023-01-31"
    assert labels["2626"] == "Peter Kullgren"
    assert all("published" not in row for row in rows)


def test_detail_keeps_location_dates_and_former_minister_categories():
    downloader = CalendarDownloader()
    rows, _ = fetch_listing(downloader, page_size=2)
    details, labels, markdown = parse_detail(downloader.details[LATEST], rows[0])
    assert details["location"] == "Stockholm"
    assert details["published"] == "2026-10-15"
    assert "updated" not in details
    assert labels["2294"] == "Kalenderhändelse"
    assert "Datum: 2026-10-15" in markdown
    assert "Plats:" in markdown and "Stockholm" in markdown
    assert "Peter Kullgren" in markdown and "Dela" not in markdown
    assert markdown.count("# Deltar vid invigningen av Ireland House") == 1
    details, labels, _ = parse_detail(downloader.details[OLDEST], rows[-1])
    assert "2625" in details["categories"]
    assert labels["2625"] == "Paulina Brandberg"
    assert rows[-1]["participants"] == ["1284"]


@pytest.mark.parametrize("bad", [None, {}, {"TotalCount": True, "Message": ""}])
def test_invalid_api_envelopes_are_rejected(bad):
    with pytest.raises(CalendarError):
        parse_fragment(bad)


@pytest.mark.parametrize("failure", ["date", "url", "missing_date", "ordinary_pages"])
def test_malformed_listing_rows_are_rejected(failure):
    response = CalendarDownloader().responses[1]
    if failure == "date":
        response["Message"] = response["Message"].replace("2023-01-23", "2023-02-31")
    elif failure == "url":
        response["Message"] = response["Message"].replace(
            OLDEST, "/kalendarium/../outside/"
        )
    elif failure == "missing_date":
        response["Message"] = response["Message"].replace(
            "timeCalSticker", "unrecognised"
        )
    else:
        downloader = CalendarDownloader()
        downloader.responses[1]["Message"] = (
            '<div class="sortcompact">ordinary page</div>'
        )
        with pytest.raises(CalendarError):
            fetch_listing(downloader, page_size=2)
        return
    with pytest.raises(CalendarError):
        parse_fragment(response)


@pytest.mark.parametrize(
    "failure", ["partial", "total", "overlap", "first_changed", "network"]
)
def test_incomplete_or_changing_api_keeps_last_export(failure, monkeypatch, tmp_path):
    downloader = CalendarDownloader()
    if failure == "partial":
        downloader.responses[2]["Message"] = ""
    elif failure == "total":
        downloader.responses[2]["TotalCount"] = 4
    elif failure == "overlap":
        downloader.responses[2]["Message"] = downloader.responses[1]["Message"]
    else:
        original = downloader.get_json

        def respond(url):
            if failure == "network":
                raise OSError("Disconnected")
            response = original(url)
            if len(downloader.calls) == 3:
                response["Message"] = response["Message"].replace(
                    "Utrikes resa", "Changed title"
                )
            return response

        monkeypatch.setattr(downloader, "get_json", respond)
    monkeypatch.setattr(calendar_export, "fetch_listing", lambda d: fetch_listing(d, 2))
    old = tmp_path / "api/kalendarium.json"
    old.parent.mkdir()
    old.write_text("[]\n")
    codes, files = {"existing": "Existing"}, {}
    assert (
        calendar_export.prepare_calendar_export(downloader, codes, files, tmp_path)
        is None
    )
    publish_json(files, tmp_path)
    assert old.read_text() == "[]\n"
    assert codes == {"existing": "Existing"}
    assert not list(tmp_path.rglob("*.md"))


def test_saved_history_is_reused_but_changed_recent_missing_and_forced_pages_refresh(
    tmp_path,
):
    downloader = CalendarDownloader()
    rows, labels = fetch_listing(downloader, page_size=2)
    row = rows[-1]
    old = row | {"published": "2023-01-23", "location": "Previously known place"}
    path = tmp_path / (OLDEST.strip("/") + ".md")
    path.parent.mkdir(parents=True)
    path.write_text("saved page")
    args = (downloader, [row], labels, {OLDEST: old}, tmp_path)
    result, markdown, failures, fetched = refresh_details(
        *args, today=date(2026, 10, 18)
    )
    assert result == [old] and not markdown and not failures and fetched == 0
    for force, today in [(True, date(2026, 10, 18)), (False, date(2023, 1, 24))]:
        assert refresh_details(*args, force=force, today=today)[3] == 1
    path.unlink()
    assert refresh_details(*args, today=date(2026, 10, 18))[3] == 1
    path.write_text("saved page")
    changed = row | {"title": "Changed title"}
    result, markdown, failures, _ = refresh_details(
        downloader, [changed], labels, {OLDEST: old}, tmp_path, today=date(2026, 10, 18)
    )
    assert result == [old] and not markdown and failures


def test_successful_export_adds_detail_labels_and_retries_unavailable_new_pages(
    monkeypatch, tmp_path
):
    downloader = CalendarDownloader()
    monkeypatch.setattr(calendar_export, "fetch_listing", lambda d: fetch_listing(d, 2))
    files, codes = {}, {}
    rows = calendar_export.prepare_calendar_export(downloader, codes, files, tmp_path)
    assert rows is not None and len(rows) == 3
    assert codes["2625"] == "Paulina Brandberg"
    assert codes["2294"] == "Kalenderhändelse"
    publish_json(files, tmp_path)
    assert "Stockholm" in (tmp_path / (LATEST.strip("/") + ".md")).read_text()
    missing = next(r for r in rows if r["url"] not in downloader.details)
    assert "published" not in missing
    assert (tmp_path / (missing["url"].strip("/") + ".md")).exists()
    downloader.pages.clear()
    calendar_export.prepare_calendar_export(downloader, codes, {}, tmp_path)
    assert OLDEST not in downloader.pages and missing["url"] in downloader.pages


def test_wrong_detail_page_or_disagreeing_dates_are_rejected():
    downloader = CalendarDownloader()
    rows, _ = fetch_listing(downloader, 2)
    with pytest.raises(CalendarError):
        parse_detail("<main><h1>Startsidan</h1></main>", rows[0])
    with pytest.raises(CalendarError):
        parse_detail(
            downloader.details[LATEST].replace(
                'datetime="2026-10-15"', 'datetime="2026-10-16"'
            ),
            rows[0],
        )


def test_detail_publication_date_is_separate_and_redirected_identity_is_rejected():
    downloader = CalendarDownloader()
    row = fetch_listing(downloader, 2)[0][0]
    html = downloader.details[LATEST].replace(
        "<head>", '<head><meta name="published" content="2026-10-01 10:00:00">'
    )
    details, _, _ = parse_detail(html, row)
    assert details["published"] == "2026-10-01"
    assert row["start_date"] == "2026-10-15"
    redirected = html.replace(
        "<head>",
        '<head><meta name="DC.Identifier" content="https://www.regeringen.se/kalendarium/other/">',
    )
    with pytest.raises(CalendarError, match="URL disagrees"):
        parse_detail(redirected, row)
