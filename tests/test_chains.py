import json
from copy import deepcopy
from pathlib import Path

import pytest

from backfill_chains import backfill
from services.chain_export import publish_json
from services.chain_parser import (
    ChainParseError,
    extract_chains,
    memberships,
    normalize_url,
)
from services.chain_records import apply_item_chain_references
from services.chain_types import Actor, Document, Observation, Phase, Stage
from services.chains import ChainStore

FIXTURES = Path(__file__).parent / "fixtures/chains"
LEGACY_URL = "/rattsliga-dokument/proposition/2019/11/prop.-20192038/"
EU_URL = "/kommenterade-dagordningar/2026/06/kommenterad-dagordning-radet-for-ekonomiska-och-finansiella-fragor-den-12-juni-2026/"


def resolve(url):
    return json.loads((FIXTURES / "redirects.json").read_text())[url]


def fixture(name):
    return (FIXTURES / f"{name}.html").read_text()


def test_legacy_wrappers_multiple_links_and_current_page():
    observation, choices = extract_chains(fixture("legacy"), LEGACY_URL)
    stages = observation["phases"][0]["actors"][0]["stages"]
    by_name = {s["name"]: s["documents"] for s in stages}
    assert len(by_name["Svensk författningssamling"]) == 2
    assert by_name["Remiss"][0]["url"].startswith("/remisser/")
    assert by_name["Statens offentliga utredningar"] == []
    assert by_name["Proposition"][0]["url"] == LEGACY_URL
    assert by_name["Proposition"][0]["current_page"]
    assert not by_name["Departementsserien"][0]["current_page"]
    assert not choices


def test_eu_phases_choices_empty_stages_and_external_documents():
    observation, choices = extract_chains(
        fixture("eu"), EU_URL, EU_URL + "?id=52025PC0989", resolve=resolve
    )
    assert len(observation["phases"]) == 3
    assert observation["celex"] == ["52025PC0989"]
    assert len(choices) == 2
    assert any("52025PC0941%3B52025PC0942%3B52025PC0943" in c for c in choices)
    documents = [d for *_, d in memberships(observation)]
    assert any(d["url"].startswith("https://eur-lex.europa.eu/") for d in documents)
    assert [d["url"] for d in documents if d["current_page"]] == [EU_URL]
    assert any(
        not s["documents"]
        for p in observation["phases"]
        for a in p["actors"]
        for s in a["stages"]
    )


def test_current_domestic_headings_exclude_tooltips():
    observation, _ = extract_chains(fixture("domestic"), "/sou/", resolve=resolve)
    stages = observation["phases"][0]["actors"][0]["stages"]
    assert stages[0]["name"] == "Kommittédirektiv"
    assert any(d["url"] == "/sou/" for *_, d in memberships(observation))


def test_domestic_continuation_keeps_both_documents_in_the_sou_stage():
    parsed, _ = extract_chains(fixture("domestic"), "/sou/", resolve=resolve)
    stages = parsed["phases"][0]["actors"][0]["stages"]
    sou = next(s for s in stages if s["name"] == "Statens offentliga utredningar")
    assert [d["url"] for d in sou["documents"]] == [
        "/sou/",
        "/rattsliga-dokument/statens-offentliga-utredningar/2025/09/sou-2025106/",
    ]
    assert not any(s["name"] is None for s in stages)


def test_tooltip_icon_does_not_mask_unrecognized_current_page_markup():
    store = ChainStore()
    html = fixture("domestic")
    store.observe(html, "/sou/", resolve=resolve)
    previous = deepcopy(store.state["observations"])
    changed = html.replace('aria-current="true"', 'data-current="true"')
    assert store.observe(changed, "/sou/", resolve=resolve) is None
    assert store.state["observations"] == previous
    assert store.failures == [
        {"source": "/sou/", "error": "Unrecognized document/current-page markup"}
    ]


def test_normalization_and_redirects():
    assert normalize_url("https://regeringen.se/foo#bar") == "/foo/"
    assert (
        normalize_url("?id=52025PC0943;52025PC0941", "/foo/", view=True)
        == "/foo/?id=52025PC0941%3B52025PC0943"
    )
    assert normalize_url("?id=", "/foo/", view=True) == "/foo/?id="
    assert (
        normalize_url("/old.aspx", resolve=lambda _: "https://www.regeringen.se/new/")
        == "/new/"
    )
    with pytest.raises(ChainParseError):
        normalize_url("/old.aspx")
    with pytest.raises(ChainParseError):
        normalize_url("javascript:alert(1)")


def observation(source, documents, celex=None) -> Observation:
    stage: Stage[Document] = {
        "name": "Stage",
        "documents": [
            {"url": url, "date": date, "title": url, "current_page": url == source}
            for url, date in documents
        ],
    }
    actor: Actor[Document] = {"name": "Government", "stages": [stage]}
    phase: Phase[Document] = {"name": "Sweden", "ongoing": True, "actors": [actor]}
    return {
        "source": source,
        "item_url": source,
        "parser_version": 1,
        "content_hash": source,
        "celex": celex or [],
        "phases": [phase],
    }


def store_with(*observations):
    store = ChainStore()
    store.state["observations"] = {o["source"]: o for o in observations}
    return store


def build_and_apply_export(store, items):
    """Simulate a completed export, including item references and remembered IDs."""
    export = store.build_export(items)
    apply_item_chain_references(items, export.item_references)
    store.update_identity_history(export)
    return export


def test_clean_rerun_is_identical_independent_of_discovery_order():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    b = observation("/b/", [("/a/", "2020"), ("/b/", "2021"), ("/c/", "2022")])
    first = store_with(a, b).build_export([{"url": "/a/"}]).collection
    second = store_with(b, a).build_export([{"url": "/a/"}]).collection
    assert first == second
    assert len(first["chains"]) == 1


def test_build_leaves_items_and_identity_history_unchanged_until_explicitly_applied():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    store = store_with(a, {**deepcopy(a), "source": "/b/"})
    store.state["assignments"] = {"/a/": "chain-A", "/b/": "chain-B"}
    items = [{"url": "/a"}, {"url": "/unrelated/", "chains": ["stale"]}]
    previous_state = deepcopy(store.state)
    previous_items = deepcopy(items)

    export = store.build_export(items)
    assert store.state == previous_state
    assert items == previous_items
    assert store.build_export(items) == export
    assert export.collection["aliases"] == {"chain-B": ["chain-A"]}

    apply_item_chain_references(items, export.item_references)
    assert items == [{"url": "/a", "chains": ["chain-A"]}, {"url": "/unrelated/"}]
    assert store.state == previous_state

    store.update_identity_history(export)
    assert store.state["assignments"] == {"/a/": "chain-A", "/b/": "chain-A"}
    assert store.state["aliases"] == {"chain-B": ["chain-A"]}


def test_failed_build_does_not_remember_unpublished_identity_changes(monkeypatch):
    import services.chains

    store = store_with(observation("/a/", [("/a/", "2020")]))
    previous_state = deepcopy(store.state)

    def fail_projection(*args):
        raise RuntimeError("Cannot build public records")

    monkeypatch.setattr(services.chains, "build_chain_records", fail_projection)
    with pytest.raises(RuntimeError, match="Cannot build public records"):
        store.build_export([])
    assert store.state == previous_state


@pytest.mark.parametrize("initial", [1, 2])
def test_refresh_retains_id_after_title_change_later_or_earlier_step(initial):
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")][:initial])
    store = store_with(a)
    chain_id = next(iter(build_and_apply_export(store, []).collection["chains"]))
    a["phases"][0]["actors"][0]["stages"][0]["documents"][0]["title"] = "Edited"
    assert (
        next(iter(build_and_apply_export(store, []).collection["chains"])) == chain_id
    )
    for url, date in [("/later/", "2025"), ("/earlier/", "1999")]:
        a["phases"][0]["actors"][0]["stages"][0]["documents"].append(
            {"url": url, "date": date, "title": url, "current_page": False}
        )
        assert (
            next(iter(build_and_apply_export(store, []).collection["chains"]))
            == chain_id
        )


def test_one_shared_document_does_not_merge_and_references_resolve():
    a = observation("/a/", [("/shared/", "2020"), ("/a/", "2021")])
    b = observation("/b/", [("/shared/", "2020"), ("/b/", "2021")])
    store = store_with(a, b)
    items = [{"url": "/shared"}, {"url": "/unrelated/", "chains": ["obsolete"]}]
    export = build_and_apply_export(store, items)
    result = export.collection
    assert len(result["chains"]) == 2
    assert len(items[0]["chains"]) == 2
    assert "chains" not in items[1]
    assert all(cid in result["chains"] for cid in items[0]["chains"])
    assert all(
        any(d["url"] == "/shared" for *_, d in memberships(c))
        for c in result["chains"].values()
    )
    assert export.report["ambiguous_matches"] == 1
    assert export.report["recheck"] == ["/a/", "/b/"]


def test_refresh_replaces_observation_failure_preserves_and_reports(tmp_path):
    store = ChainStore(tmp_path / "state.json")
    store.observe(fixture("legacy"), LEGACY_URL)
    original = deepcopy(store.state["observations"])
    assert store.observe(None, LEGACY_URL) is None
    assert store.observe('<div id="accordion--chain">broken</div>', LEGACY_URL) is None
    assert store.state["observations"] == original
    export = build_and_apply_export(store, [])
    assert export.report["parser_failures"] == 2
    store.save()
    restored = ChainStore(tmp_path / "state.json")
    assert restored.state == store.state
    restored.observe(
        fixture("legacy").replace("202080.html", "202099.html"), LEGACY_URL
    )
    assert len(restored.state["observations"]) == 1
    assert (
        restored.state["observations"][LEGACY_URL]["content_hash"]
        != original[LEGACY_URL]["content_hash"]
    )


def test_conflicting_views_are_preserved_and_missing_members_are_not_deleted():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021"), ("/c/", "2022")])
    b = observation("/b/", [("/a/", "2020"), ("/b/", "2021")])
    b["phases"][0]["actors"][0]["stages"][0]["documents"][0]["title"] = (
        "Conflicting title"
    )
    store = store_with(a, b)
    export = build_and_apply_export(store, [])
    result = export.collection
    assert len(result["chains"]) == 1
    docs = [d for c in result["chains"].values() for *_, d in memberships(c)]
    assert len([d for d in docs if d["url"] == "/a/"]) == 2
    assert any(d["url"] == "/c/" for d in docs)
    assert export.report["conflicting_observations"] == 1


def test_merge_keeps_the_smallest_previous_id_and_aliases_the_other():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    b = observation("/b/", [("/b/", "2021"), ("/c/", "2022")])
    store = store_with(a, b)
    old = set(build_and_apply_export(store, []).collection["chains"])
    # /a/ and /b/ start with different anchor pairs, then /b/ adopts /a/'s pair.
    store.state["observations"]["/b/"] = {**deepcopy(a), "source": "/b/"}
    merged = build_and_apply_export(store, []).collection
    assert len(merged["chains"]) == 1
    remaining = next(iter(merged["chains"]))
    assert remaining == min(old)
    assert merged["aliases"][next(iter(old - {remaining}))] == [remaining]


def test_split_keeps_one_previous_id_and_aliases_all_successors():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    b = observation("/b/", [("/b/", "2021"), ("/c/", "2022")])
    store = store_with(a, {**deepcopy(a), "source": "/b/"})
    remaining = next(iter(build_and_apply_export(store, []).collection["chains"]))
    # The previously shared chain separates into two anchor pairs. Consumers
    # holding the old ID must discover both successors, even though it stays live.
    store.state["observations"]["/b/"] = b
    split = build_and_apply_export(store, []).collection
    assert len(split["chains"]) == 2
    assert remaining in split["chains"]
    assert set(split["aliases"][remaining]) == set(split["chains"])


def test_old_merge_alias_resolves_directly_to_all_live_successors_after_a_split():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    b = observation("/b/", [("/b/", "2021"), ("/c/", "2022")])
    store = store_with(a, b)
    original_ids = set(build_and_apply_export(store, []).collection["chains"])
    store.state["observations"]["/b/"] = {**deepcopy(a), "source": "/b/"}
    merged = build_and_apply_export(store, []).collection
    retained_id = next(iter(merged["chains"]))
    retired_id = next(iter(original_ids - {retained_id}))

    store.state["observations"]["/b/"] = b
    split = build_and_apply_export(store, []).collection
    assert set(split["aliases"][retired_id]) == set(split["chains"])


def test_multiselect_celex_sets_remain_distinct():
    docs = [("/shared/", "2020"), ("/other/", "2021")]
    store = store_with(
        observation("/a/", docs, ["52025PC0941"]),
        observation("/b/", docs, ["52025PC0941", "52025PC0942"]),
    )
    assert len(store.build_export([]).collection["chains"]) == 2


def test_backfill_resumes_and_retries_failure(tmp_path):
    class Downloader:
        calls = []

        def get_webpage(self, url):
            self.calls.append(url)
            return None if url == "/fail/" else fixture("legacy")

    downloader = Downloader()
    store = ChainStore(tmp_path / "state.json")
    items = [{"url": "/ok/"}, {"url": "/fail/"}, {"url": "/later/"}]
    assert backfill(items, store, downloader, limit=2) == 2
    assert store.state["completed"] == ["/ok/"]
    restored = ChainStore(tmp_path / "state.json")
    assert backfill(items, restored, downloader) == 2
    assert downloader.calls == ["/ok/", "/fail/", "/fail/", "/later/"]


@pytest.fixture
def recheck_runner(monkeypatch, tmp_path):
    import backfill_chains

    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/types.json").write_text("[]")
    api = tmp_path / "data/api"
    api.mkdir(parents=True)
    # Queued sources need not still occur in the item index or current chooser.
    (api / "items.json").write_text("[]")
    calls = []
    pages = {}

    class Downloader:
        b = type("Browser", (), {"close": lambda self: None})()

        def get_webpage(self, url):
            calls.append(url)
            page = pages[url]
            if isinstance(page, Exception):
                raise page
            return page

    monkeypatch.setattr(backfill_chains, "Downloader", Downloader)

    def run(report=None, limit=None):
        if report is not None:
            (api / "chains-report.json").write_text(json.dumps(report))
        args = ["backfill_chains.py", "--recheck"]
        if limit is not None:
            args.extend(["--limit", str(limit)])
        monkeypatch.setattr("sys.argv", args)
        backfill_chains.main()
        return json.loads((api / "chains-report.json").read_text())

    return run, pages, calls, tmp_path


@pytest.mark.parametrize("selector", ["", "52025PC0989", "52025PC0942;52025PC0941"])
def test_recheck_fetches_exact_queued_selector_without_a_chooser(
    recheck_runner, selector
):
    run, pages, calls, root = recheck_runner
    source = normalize_url("/a/?id=" + selector, view=True)
    pages[source] = fixture("legacy")
    report = run(
        {"recheck": [source], "failures": [{"source": source, "error": "Timeout"}]}
    )
    assert calls == [source]
    store = ChainStore(root / "data/.chain-state/state.json")
    parsed = store.state["observations"][source]
    assert parsed["item_url"] == "/a/"
    assert {d["url"] for *_, d in memberships(parsed) if d["current_page"]} == {"/a/"}
    assert report["failures"] == report["recheck"] == []


def test_bounded_recheck_preserves_unattempted_failures_and_resumes(recheck_runner):
    run, pages, calls, _ = recheck_runner
    pages.update(
        {url: '<div class="col-1"><h1>No chain</h1></div>' for url in ("/a/", "/b/")}
    )
    failures = [{"source": url, "error": "Previous timeout"} for url in pages]
    report = run({"recheck": list(pages), "failures": failures}, limit=1)
    assert calls == ["/a/"]
    assert report["recheck"] == ["/b/"]
    assert report["failures"] == [failures[1]]
    assert report["parser_failures"] == 1
    report = run(limit=1)
    assert calls == ["/a/", "/b/"]
    assert report["failures"] == report["recheck"] == []


def test_recheck_retains_observation_and_queues_a_new_failure(recheck_runner):
    run, pages, calls, root = recheck_runner
    source = "/a/?id=52025PC0989"
    store = ChainStore(root / "data/.chain-state/state.json")
    store.observe(fixture("legacy"), "/a/", source)
    previous = deepcopy(store.state["observations"])
    store.save()
    pages[source] = TimeoutError("New timeout")
    report = run(
        {"recheck": [source], "failures": [{"source": source, "error": "Old timeout"}]}
    )
    assert calls == [source]
    assert ChainStore(store.path).state["observations"] == previous
    assert report["recheck"] == [source]
    assert report["failures"] == [{"source": source, "error": "New timeout"}]


def test_failed_staging_does_not_modify_public_export(tmp_path):
    path = tmp_path / "api/items.json"
    path.parent.mkdir()
    path.write_text("old")
    with pytest.raises(TypeError):
        publish_json({"api/items.json": [], "api/chains.json": object()}, tmp_path)
    assert path.read_text() == "old"
    assert not (tmp_path / "api/chains.json").exists()


def test_empty_selector_and_alternate_view_failure_preserve_observation():
    html = fixture("eu").replace("?id=52021PC0564", "?id=")
    store = ChainStore()
    failed_view = EU_URL + "?id="
    store.observe(html, EU_URL, failed_view, resolve)
    previous = deepcopy(store.state["observations"][failed_view])

    class Downloader:
        calls = []

        def get_webpage(self, url):
            self.calls.append(url)
            if url == failed_view:
                raise TimeoutError("Test timeout")
            return html

    downloader = Downloader()
    assert not store.fetch_views(html, EU_URL, downloader, resolve)
    assert failed_view in downloader.calls
    assert len(downloader.calls) == len(set(downloader.calls)) == 2
    assert store.state["observations"][failed_view] == previous
    assert store.failures == [{"source": failed_view, "error": "Test timeout"}]


def test_local_pdf_url_and_multiple_dates_in_a_stage():
    assert normalize_url("/contentassets/a.pdf") == "/contentassets/a.pdf"
    html = """<nav class="c-accordion-block"><div class="c-accordion">
    <h2 class="c-accordion-head__title">Phase</h2>
    <div class="c-accordion__items"><h3 class="c-accordion-plain__action">Actor</h3>
    <div class="c-list-content"><div class="c-list-content__title"><strong>Stage</strong></div>
    <time datetime="2020-01-01"></time><div><a class="c-list-content__link" href="/a/">A</a></div>
    <time datetime="2021-01-01"></time><div><a class="c-list-content__link" href="/b/">B</a></div>
    </div></div></div></nav>"""
    parsed, _ = extract_chains(html, "/a/")
    assert [(d["url"], d["date"]) for *_, d in memberships(parsed)] == [
        ("/a/", "2020-01-01"),
        ("/b/", "2021-01-01"),
    ]


def test_recognized_absence_removes_only_its_own_observation():
    a = observation("/a/", [("/a/", "2020"), ("/b/", "2021")])
    b = {**deepcopy(a), "source": "/b/"}
    store = store_with(a, b)
    before = set(build_and_apply_export(store, []).collection["chains"])
    store.observe('<div class="col-1"><h1>No chain here</h1></div>', "/a/")
    assert set(build_and_apply_export(store, []).collection["chains"]) == before


def test_unknown_layout_does_not_clear_previous_observation():
    store = store_with(observation("/a/", [("/a/", "2020")]))
    before = deepcopy(store.state["observations"])
    store.observe(
        '<div class="col-1"><h1>Title</h1><h2>Lagstiftningskedja</h2><section>New format</section></div>',
        "/a/",
    )
    assert store.state["observations"] == before


def test_main_exports_matching_items_types_and_chains(monkeypatch, tmp_path):
    import fetch
    from services.item_refresh import RefreshPlan

    class Downloader:
        b = type("Browser", (), {"close": lambda self: None})()

        def get_webpage(self, url):
            return '<div class="col-1"><h1>Title</h1></div>' + fixture("legacy")

    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/types.json").write_text('["rattsliga-dokument/proposition"]')
    item = {"url": LEGACY_URL, "title": "Title", "types": [], "senders": []}
    monkeypatch.setattr(fetch, "Downloader", Downloader)
    monkeypatch.setattr(
        fetch, "prepare_items", lambda *args: ([item], {}, RefreshPlan())
    )
    fetch.main()
    items = json.loads((tmp_path / "data/api/items.json").read_text())
    types = json.loads(
        (tmp_path / "data/rattsliga-dokument/proposition.json").read_text()
    )
    collection = json.loads((tmp_path / "data/api/chains.json").read_text())
    assert items == types
    assert all(cid in collection["chains"] for item in items for cid in item["chains"])
    assert (tmp_path / "data/.chain-state/state.json").exists()
