import json
from copy import deepcopy

from services.chain_reconciliation import Reconciliation, assign_public_ids
from services.chain_reporting import render_normalization_report, report_normalizations
from services.chain_types import ChainItem, Document, Observation, Stage
from services.chains import ChainStore

IDENTITY = "chain-0123456789abcdef" + "0" * 48
PUBLIC_ID = "0123456789abcdef"


def document(url, date=None, title="Source title") -> Document:
    return {"url": url, "date": date, "title": title, "current_page": False}


def store_for(stages: list[Stage[Document]], path=None) -> ChainStore:
    observation: Observation = {
        "source": "/source/",
        "item_url": "/source/",
        "parser_version": 1,
        "celex": [],
        "identity_celex": [],
        "content_hash": "fixture",
        "phases": [
            {
                "name": "Lagstiftning i Sverige",
                "ongoing": None,
                "actors": [{"name": "Regeringen", "stages": stages}],
            }
        ],
    }
    store = ChainStore(path)
    store.state["observations"] = {"/source/": observation}
    store.state["assignments"] = {"/source/": IDENTITY}
    return store


def public_stages(export):
    return export.collection["chains"][PUBLIC_ID]["phases"][0]["actors"][0]["stages"]


def test_assembly_constructs_the_agreed_lean_schema_and_keeps_date_exceptions():
    ds = "/rattsliga-dokument/departementsserien-och-promemorior/2020/01/example/"
    remiss = "/remisser/2020/02/example/"
    sfs = "https://svenskforfattningssamling.se/doc/202080.html"
    store = store_for(
        [
            {"name": "Kommittédirektiv", "documents": []},
            {
                "name": "Departementsserien",
                "documents": [document(ds, "2020-01-01 12:34:56")],
            },
            {
                "name": "Remiss",
                "documents": [
                    document(remiss, "2020-02-03", "Remiss av X"),
                    document(remiss, "2020-02-03", "Remissinstanser för X"),
                ],
            },
            {
                "name": "Svensk författningssamling",
                "documents": [document(sfs, "2020-03-06", "Lag (2020:80)")],
            },
        ]
    )
    items: list[ChainItem] = [
        {"url": ds, "title": "Canonical title", "published": "2020-01-01"},
        {"url": remiss, "title": "Canonical remiss title", "published": "2020-02-02"},
    ]
    previous = deepcopy(store.state)
    export = store.build_export(items, normalize=False)
    assert export.collection == {
        "chains": {
            PUBLIC_ID: {
                "phases": [
                    {
                        "name": "Lagstiftning i Sverige",
                        "actors": [
                            {
                                "name": "Regeringen",
                                "stages": [
                                    {"type": "1325", "documents": [{"url": ds}]},
                                    {
                                        "type": "2099",
                                        "documents": [
                                            {"url": remiss, "date": "2020-02-03"}
                                        ],
                                    },
                                    {
                                        "type": "sfs",
                                        "documents": [
                                            {
                                                "url": sfs,
                                                "title": "Lag (2020:80)",
                                                "date": "2020-03-06",
                                            }
                                        ],
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }
    assert store.state == previous
    assert "chains" not in items[0]


def test_normalization_preserves_order_evidence_and_unresolvable_headings():
    remiss = "/remisser/2023/10/example/"
    sou1 = "/rattsliga-dokument/statens-offentliga-utredningar/2020/01/one/"
    ds = "/rattsliga-dokument/departementsserien-och-promemorior/2020/02/two/"
    sou2 = "/rattsliga-dokument/statens-offentliga-utredningar/2020/03/three/"
    unknown = "/informationsmaterial/2020/01/example/"
    store = store_for(
        [
            {"name": "Remss", "documents": [document(remiss)]},
            {
                "name": "Övriga utredningar",
                "documents": [document(sou1), document(ds), document(sou2)],
            },
            {"name": "Uppdrag", "documents": [document(unknown)]},
        ]
    )
    items: list[ChainItem] = [
        {"url": "/source/", "published": "2026-01-01", "senders": ["1287"]}
    ]
    before = deepcopy(store.state)
    unnormalized = store.build_export(items, normalize=False)
    export = store.build_export(items, codes={"1287": "Justitiedepartementet"})
    stages = public_stages(export)
    assert [s.get("type") for s in stages] == ["2099", "1331", "1325", "1331", None]
    assert stages[-1]["name"] == "Uppdrag"
    assert [d for s in stages for d in s["documents"]] == [
        d for s in public_stages(unnormalized) for d in s["documents"]
    ]
    findings = export.normalization_report["findings"]
    assert {f["kind"] for f in findings} == {
        "normalized_stage",
        "split_stage",
        "unresolved_stage",
    }
    assert all(f["chain"] == PUBLIC_ID and f["source"] == "/source/" for f in findings)
    assert all(f["departments"] == ["Justitiedepartementet"] for f in findings)
    assert export.report["recheck"] == ["/source/"]
    assert store.state == before
    assert export == store.build_export(items, codes={"1287": "Justitiedepartementet"})


def test_conflicting_metadata_dates_and_actor_groups_are_reviewed_without_guesses():
    ds = "/rattsliga-dokument/departementsserien-och-promemorior/2021/03/draft/"
    store = store_for(
        [{"name": "Lagrådsremiss", "documents": [document(ds, "2021-03-02")]}]
    )
    store.state["observations"]["/source/"]["phases"][0]["actors"][0]["name"] = (
        "EU-beslut"
    )
    items: list[ChainItem] = [
        {
            "url": ds,
            "title": "Utkast till lagrådsremiss",
            "types": ["2085"],
            "published": "2021-03-01",
        }
    ]
    export = store.build_export(items)
    phase = export.collection["chains"][PUBLIC_ID]["phases"][0]
    assert phase["actors"][0]["name"] == "EU-beslut"
    assert public_stages(export)[0] == {
        "type": "2085",
        "documents": [{"url": ds, "date": "2021-03-02"}],
    }
    findings = export.normalization_report["findings"]
    assert {f["kind"] for f in findings} == {
        "actor_group",
        "date_discrepancy",
        "document_type_conflict",
    }
    assert all(f["status"] == "review" for f in findings)


def test_colliding_new_ids_extend_without_renaming_or_reusing_published_ids():
    common = "a" * 16
    old = "chain-" + common + "f" * 48
    new = "chain-" + common + "0" * 48
    retired = "chain-" + "b" * 64
    previous = {old: common, retired: "b" * 16}
    reconciliation = Reconciliation(
        groups={new: [], old: []}, assignments={}, aliases={}
    )
    ids = assign_public_ids(reconciliation, previous)
    assert ids[old] == common
    assert ids[new] == common + "00"
    assert ids[retired] == "b" * 16
    assert ids == assign_public_ids(reconciliation, ids)
    assert previous == {old: common, retired: "b" * 16}


def test_short_id_registry_survives_save_and_rebuild(tmp_path):
    store = store_for(
        [{"name": "Remss", "documents": [document("/remisser/example/")]}],
        tmp_path / "state.json",
    )
    first = store.build_export([])
    store.update_identity_history(first)
    store.save()
    restored = ChainStore(store.path)
    assert restored.state["assignments"] == {"/source/": IDENTITY}
    assert restored.state["public_ids"] == {IDENTITY: PUBLIC_ID}
    assert first.collection == restored.build_export([]).collection


def test_actions_summary_is_bounded_and_full_artifact_retains_original_values(
    monkeypatch, tmp_path, capsys
):
    long_name = "Odd heading | <tag>\n" + "x" * 400
    store = store_for(
        [{"name": long_name, "documents": [document("/remisser/example/")]}]
    )
    report = store.build_export([]).normalization_report
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    report_normalizations(report)
    summary = (tmp_path / "summary.md").read_text()
    assert len(summary.encode()) < 40_000
    assert "&lt;tag&gt;" in summary and "\\|" in summary
    assert "New findings: **1**" in summary
    artifact = json.loads(
        (tmp_path / "chain-normalization/normalization.json").read_text()
    )
    assert artifact == report
    assert artifact["findings"][0]["before"] == long_name
    assert "Odd heading" not in capsys.readouterr().out
    unchanged = render_normalization_report(
        report, report, max_rows=20, max_bytes=40_000
    )
    assert "New findings: **0**" in unchanged
    resolved = render_normalization_report(
        {"version": 1, "summary": {}, "findings": [], "recheck": []}, report
    )
    assert "No longer observed: **1**" in resolved


def test_export_only_rebuilds_without_browser_and_updates_all_references(
    monkeypatch, tmp_path
):
    import backfill_chains

    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/types.json").write_text('["remisser"]')
    api = tmp_path / "data/api"
    api.mkdir(parents=True)
    item = {"url": "/remisser/example/", "title": "Canonical title", "types": ["2099"]}
    (api / "items.json").write_text(json.dumps([item]))
    failure = {"source": "/unavailable/", "error": "Previous timeout"}
    (api / "chains-report.json").write_text(
        json.dumps({"failures": [failure], "recheck": ["/unavailable/"]})
    )
    store = store_for(
        [{"name": "Remss", "documents": [document(item["url"])]}],
        tmp_path / "data/.chain-state/state.json",
    )
    store.save()

    def no_browser():
        raise AssertionError("export-only must not start a browser")

    monkeypatch.setattr(backfill_chains, "Downloader", no_browser)
    monkeypatch.setattr(backfill_chains, "report_normalizations", lambda *args: None)
    monkeypatch.setattr("sys.argv", ["backfill_chains.py", "--export-only"])
    backfill_chains.main()
    collection = (api / "chains.json").read_bytes()
    assert set(json.loads(collection)) == {"chains"}
    items = json.loads((api / "items.json").read_text())
    assert items[0]["chains"] == [PUBLIC_ID]
    assert json.loads((tmp_path / "data/remisser.json").read_text()) == items
    assert (
        json.loads((api / "chains-normalization.json").read_text())["summary"][
            "normalized_stages"
        ]
        == 1
    )
    quality = json.loads((api / "chains-report.json").read_text())
    assert quality["failures"] == [failure]
    assert "/unavailable/" in quality["recheck"]
    backfill_chains.main()
    assert (api / "chains.json").read_bytes() == collection
    from audit_chain_types import analyse

    audit = analyse(tmp_path / "data")
    assert audit["summary"]["exotic_stages"] == 1
    assert audit["exotic_stages"][0]["name"] == "Remss"


def test_corrected_source_resolves_finding_without_changing_identity_or_public_membership():
    store = store_for(
        [{"name": "Remss", "documents": [document("/remisser/example/")]}]
    )
    first = store.build_export([])
    store.update_identity_history(first)
    store.state["observations"]["/source/"]["phases"][0]["actors"][0]["stages"][0][
        "name"
    ] = "Remiss"
    corrected = store.build_export([])
    assert corrected.collection == first.collection
    assert corrected.normalization_report["findings"] == []
    summary = render_normalization_report(
        corrected.normalization_report, first.normalization_report
    )
    assert "No longer observed: **1**" in summary
