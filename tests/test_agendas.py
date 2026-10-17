import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from selectolax.lexbor import LexborHTMLParser

from services.agendas import AgendaError, fetch_agendas
from services.agendas import export as agenda_export
from services.agendas.fetcher import apply_weekly_context
from services.agendas.parser import (
    LISTING,
    heading_date,
    listing_root,
    parse_fragment,
    weekly_context,
)
from services.chains.export import publish_json
from services.web_parser import extract_page

pytestmark = pytest.mark.smoke
FIXTURES = Path(__file__).parent / "fixtures/agendas"
SOURCE = "/regeringsarenden/regeringsarenden-vecka-42-2026/"
PRODUCT_TITLE = "Regeringens proposition\nEn ny produktansvarslag"


class AgendaDownloader:
    def __init__(self):
        self.b = self
        self.weekly = (FIXTURES / "weekly.html").read_text()
        self.responses = {
            n: json.loads((FIXTURES / f"page-{n}.json").read_text()) for n in (1, 2)
        }
        self.calls = []
        self.pages = []

    def get_json(self, url):
        query = parse_qs(urlsplit(url).query)
        assert query["filterType"] == ["Structure"]
        assert query["filterByType"] == ["CasePage"]
        assert query["rootPageReference"] == ["664600"]
        assert query["pageSize"] == ["2"]
        page = int(query["page"][0])
        self.calls.append(page)
        return deepcopy(self.responses[page])

    def get_webpage(self, url):
        self.pages.append(url)
        assert url in {LISTING, SOURCE}
        if url == LISTING:
            return (FIXTURES / "weekly.html").read_text()
        return self.weekly


def test_fragment_preserves_multiline_titles_and_incomplete_journal_identifiers():
    downloader = AgendaDownloader()
    rows = [
        r
        for response in downloader.responses.values()
        for r in parse_fragment(response)[1]
    ]
    product = next(r for r in rows if "produktansvarslag" in r["title"])
    assert product == {
        "source": SOURCE,
        "year": 2026,
        "week": 42,
        "department": "Justitiedepartementet",
        "minister": "Gunnar Strömmer",
        "title": PRODUCT_TITLE,
        "agenda_number": "I:10",
        "journal_ids": ["Ju2025/02091", "Ju2026/01836", "Ju2026/"],
        "responsible_official": "Jonas Pontén",
    }
    assert sum(r["agenda_number"] == "III:1" for r in rows) == 2


def test_weekly_markdown_keeps_hierarchy_and_omits_duplicate_filter_results():
    html = (FIXTURES / "weekly.html").read_text()
    markdown, _ = extract_page(html, SOURCE)
    assert markdown.startswith("# Regeringsärenden vecka 42, 2026\n")
    assert "## Regeringssammanträdet torsdag den 15 oktober" in markdown
    assert "### Justitiedepartementet" in markdown
    assert "#### Föredragande statsråd:" in markdown
    assert "Gunnar Strömmer" in markdown
    assert "##### Regeringens proposition" in markdown
    assert markdown.count("En ny produktansvarslag") == 1
    assert markdown.count("Regeringsärendenummer:") == 3
    rows, labels = weekly_context(html, SOURCE, 2026, 42)
    assert len(rows) == 3
    assert {r["meeting_date"] for r in rows} == {"2026-10-15"}
    assert labels["1287"] == "Justitiedepartementet"


def test_full_snapshot_paginates_once_then_checks_consistency_and_reuses_codes():
    downloader = AgendaDownloader()
    result = fetch_agendas(downloader, {}, page_size=2)
    assert downloader.calls == [1, 2, 1]
    assert downloader.pages == [LISTING, SOURCE]
    assert len(result.records) == 3
    assert result.undated_sources == []
    product = next(r for r in result.records if r["title"] == PRODUCT_TITLE)
    assert product["meeting_date"] == "2026-10-15"
    assert product["department_code"] == "1287"
    assert product["minister_code"] == "2615"
    # Server result order must not determine the published record order.
    tree = LexborHTMLParser(downloader.responses[1]["Message"])
    blocks = tree.css(".sortcompact.sortextended")
    downloader.responses[1]["Message"] = "".join(b.html or "" for b in reversed(blocks))
    assert fetch_agendas(downloader, {}, page_size=2).records == result.records


@pytest.mark.parametrize(
    "failure",
    [
        "empty",
        "changed_total",
        "invalid_shape",
        "overlap",
        "exception",
        "changed_first_page",
    ],
)
def test_incomplete_snapshots_fail_instead_of_publishing_partial_records(
    failure, monkeypatch
):
    downloader = AgendaDownloader()
    if failure == "empty":
        downloader.responses[2]["Message"] = ""
    elif failure == "changed_total":
        downloader.responses[2]["TotalCount"] = 4
    elif failure == "invalid_shape":
        downloader.responses[2] = {"Message": "Service unavailable"}
    elif failure == "overlap":
        tree = LexborHTMLParser(downloader.responses[1]["Message"])
        block = tree.css_first(".sortcompact.sortextended")
        assert block is not None
        downloader.responses[2]["Message"] = block.html
    else:
        original = downloader.get_json

        def fail(url):
            if failure == "exception":
                raise OSError("Disconnected")
            response = original(url)
            if len(downloader.calls) == 3:
                response["Message"] += "changed"
            return response

        monkeypatch.setattr(downloader, "get_json", fail)
    with pytest.raises(AgendaError):
        fetch_agendas(downloader, {}, page_size=2)


def test_unverifiable_weekly_source_does_not_invent_meeting_dates():
    downloader = AgendaDownloader()
    downloader.weekly = '<div class="col-1"><h1>Regeringen.se</h1></div>'
    result = fetch_agendas(downloader, {}, page_size=2)
    assert len(result.records) == 3
    assert all(r["meeting_date"] is None for r in result.records)
    assert result.undated_sources == [SOURCE]
    assert result.pages == {}


def test_weekly_heading_recovers_a_minister_missing_from_api():
    downloader = AgendaDownloader()
    for response in downloader.responses.values():
        response["Message"] = response["Message"].replace("Gunnar Strömmer, ", "")
    assert (
        next(
            r
            for r in parse_fragment(downloader.responses[1])[1]
            if r["title"] == PRODUCT_TITLE
        )["minister"]
        is None
    )
    result = fetch_agendas(downloader, {}, page_size=2)
    product = next(r for r in result.records if r["title"] == PRODUCT_TITLE)
    assert product["minister"] == "Gunnar Strömmer"
    assert product["minister_code"] == "2615"


def test_partial_weekly_body_rejects_snapshot_instead_of_truncating_markdown():
    downloader = AgendaDownloader()
    tree = LexborHTMLParser(downloader.weekly)
    tree.css(".c-faq__accordion")[0].decompose()
    downloader.weekly = tree.html or ""
    with pytest.raises(AgendaError, match="Weekly agenda and API entries disagree"):
        fetch_agendas(downloader, {}, page_size=2)


def test_multiple_meeting_dates_are_matched_per_entry_and_ambiguity_stays_unknown():
    entries = parse_fragment(AgendaDownloader().responses[1])[1]
    context = [
        dict(entries[0], meeting_date="2026-10-15"),
        dict(entries[1], meeting_date="2026-10-16"),
    ]
    apply_weekly_context(entries, context)
    assert [r["meeting_date"] for r in entries] == ["2026-10-15", "2026-10-16"]
    same = parse_fragment(AgendaDownloader().responses[1])[1][0]
    ambiguous = [same.copy(), same.copy()]
    apply_weekly_context(
        ambiguous,
        [dict(same, meeting_date="2026-10-15"), dict(same, meeting_date="2026-10-16")],
    )
    assert all(r["meeting_date"] is None for r in ambiguous)


@pytest.mark.parametrize(
    "heading,year,week,expected",
    [
        ("Regeringssammanträdet torsdag den 15 oktober", 2026, 42, "2026-10-15"),
        ("Regeringssammanträdet måndag den 30 december", 2020, 1, "2019-12-30"),
        ("Regeringssammanträdet den 15 oktober 2026", 2026, 42, "2026-10-15"),
        ("Regeringssammanträdet", 2026, 42, None),
        ("Regeringssammanträdet den 31 februari", 2026, 8, None),
    ],
)
def test_meeting_dates_come_from_source_headings(heading, year, week, expected):
    assert heading_date(heading, year, week) == expected


def test_missing_minister_and_blank_identifiers_stay_unknown():
    response = {
        "TotalCount": 1,
        "Message": f"""
        <div class="sortcompact sortextended">
          <p class="sortextended__excerpt"><strong>RA-37230</strong></p>
          <p class="sortextended__excerpt">Regeringsärendenummer: · Ansvarig chefstjänsteman:</p>
          <div class="block--timeLinks"><p>
            <a href="{SOURCE}">Regeringsärenden vecka 42, 2026</a> · Utbildningsdepartementet
          </p></div>
        </div>
        """,
    }
    row = parse_fragment(response)[1][0]
    assert row["minister"] is None
    assert row["agenda_number"] is None
    assert row["journal_ids"] == []
    assert row["responsible_official"] is None


@pytest.mark.parametrize("failure", ["api", "weekly_request"])
def test_failed_refresh_keeps_last_complete_export_and_codes(
    monkeypatch, tmp_path, failure
):
    old = tmp_path / "api/regeringsarenden.json"
    old.parent.mkdir()
    old.write_text('[{"title":"Last complete snapshot"}]\n')
    before = old.read_bytes()
    downloader = AgendaDownloader()
    if failure == "api":
        downloader.responses[2]["Message"] = ""
    else:
        get_page = downloader.get_webpage
        monkeypatch.setattr(
            downloader,
            "get_webpage",
            lambda url: get_page(url) if url == LISTING else None,
        )
    monkeypatch.setattr(
        agenda_export, "fetch_agendas", lambda d, c: fetch_agendas(d, c, page_size=2)
    )
    files, codes = {}, {"existing": "Existing code"}
    assert (
        agenda_export.prepare_agenda_export(downloader, codes, files, tmp_path) is None
    )
    publish_json(files, tmp_path)
    assert old.read_bytes() == before
    assert codes == {"existing": "Existing code"}
    assert not list(tmp_path.rglob("*.md"))


def test_successful_refresh_replaces_entries_and_repairs_weekly_markdown(
    monkeypatch, tmp_path
):
    downloader = AgendaDownloader()
    monkeypatch.setattr(
        agenda_export, "fetch_agendas", lambda d, c: fetch_agendas(d, c, page_size=2)
    )
    files, codes = {}, {}
    agenda_export.prepare_agenda_export(downloader, codes, files, tmp_path)
    assert len(files["api/regeringsarenden.json"]) == 3
    assert codes["1287"] == "Justitiedepartementet"
    markdown_path = tmp_path / (SOURCE.strip("/") + ".md")
    assert markdown_path.read_text().count("En ny produktansvarslag") == 1

    original_write = agenda_export.Writer.write_md

    def unexpected_write(*args):
        raise AssertionError("Unchanged weekly Markdown must not be rewritten")

    monkeypatch.setattr(agenda_export.Writer, "write_md", unexpected_write)
    agenda_export.prepare_agenda_export(downloader, codes, files, tmp_path)
    assert len(files["api/regeringsarenden.json"]) == 3
    monkeypatch.setattr(agenda_export.Writer, "write_md", original_write)
    for response in downloader.responses.values():
        response["Message"] = response["Message"].replace(
            "En ny produktansvarslag", "En uppdaterad produktansvarslag"
        )
    downloader.weekly = downloader.weekly.replace(
        "En ny produktansvarslag", "En uppdaterad produktansvarslag"
    )
    agenda_export.prepare_agenda_export(downloader, codes, files, tmp_path)
    assert len(files["api/regeringsarenden.json"]) == 3
    assert not any(
        r["title"] == PRODUCT_TITLE for r in files["api/regeringsarenden.json"]
    )
    assert markdown_path.read_text().count("En uppdaterad produktansvarslag") == 1


def test_root_reference_is_discovered_and_ambiguous_roots_are_rejected():
    assert listing_root(
        '<div data-filterbytype="CasePage" data-rootpage="123"></div>'
    ) == ("123", {})
    with pytest.raises(AgendaError):
        listing_root('<div data-filterbytype="CasePage" data-rootpage="123"></div>' * 2)
