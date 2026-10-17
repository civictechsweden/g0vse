import json
from copy import deepcopy

from services.chains import ChainStore
from services.chains.reconciliation import assign_public_ids
from services.chains.reporting import render_normalization_report, report_normalizations
from services.chains.types import (
    ChainCollection,
    ChainItem,
    Document,
    Observation,
    Stage,
)


def document(url, date=None, title="Source title") -> Document:
    return {"url": url, "date": date, "title": title, "current_page": False}


def store_for(stages: list[Stage[Document]]) -> ChainStore:
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
    store = ChainStore()
    store.observations = {"/source/": observation}
    return store


def public_stages(export):
    return next(iter(export.collection["chains"].values()))["phases"][0]["actors"][0][
        "stages"
    ]


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
    previous = deepcopy(store.observations)
    export = store.build_export(items, normalize=False)
    assert export.collection == {
        "chains": {
            next(iter(export.collection["chains"])): {
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
    assert store.observations == previous
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
    before = deepcopy(store.observations)
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
    assert all(
        f["chain"] == next(iter(export.collection["chains"]))
        and f["source"] == "/source/"
        for f in findings
    )
    assert all(f["departments"] == ["Justitiedepartementet"] for f in findings)
    assert export.report["recheck"] == ["/source/"]
    assert store.observations == before
    assert export == store.build_export(items, codes={"1287": "Justitiedepartementet"})


def test_conflicting_metadata_dates_and_actor_groups_are_reviewed_without_guesses():
    ds = "/rattsliga-dokument/departementsserien-och-promemorior/2021/03/draft/"
    store = store_for(
        [{"name": "Lagrådsremiss", "documents": [document(ds, "2021-03-02")]}]
    )
    store.observations["/source/"]["phases"][0]["actors"][0]["name"] = "EU-beslut"
    items: list[ChainItem] = [
        {
            "url": ds,
            "title": "Utkast till lagrådsremiss",
            "types": ["2085"],
            "published": "2021-03-01",
        }
    ]
    export = store.build_export(items)
    phase = next(iter(export.collection["chains"].values()))["phases"][0]
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


def test_actions_writes_only_a_bounded_markdown_summary(monkeypatch, tmp_path, capsys):
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
    assert "Stage name normalized" in summary
    assert list(tmp_path.iterdir()) == [tmp_path / "summary.md"]
    assert report["findings"][0]["before"] == long_name
    assert "Odd heading" not in capsys.readouterr().out


def test_corrected_source_resolves_finding_without_changing_identity_or_public_membership():
    store = store_for(
        [{"name": "Remss", "documents": [document("/remisser/example/")]}]
    )
    first = store.build_export([])
    store.baseline = deepcopy(first.collection)
    store.observations["/source/"]["phases"][0]["actors"][0]["stages"][0]["name"] = (
        "Remiss"
    )
    corrected = store.build_export([])
    assert corrected.collection == first.collection
    assert corrected.normalization_report["findings"] == []
    summary = render_normalization_report(corrected.normalization_report)
    assert "No normalization findings" in summary


def test_published_collection_is_the_only_input_needed_to_keep_history(tmp_path):
    remiss = "/remisser/example/"
    original = store_for([{"name": "Remiss", "documents": [document(remiss)]}])
    baseline = original.build_export([]).collection
    path = tmp_path / "chains.json"
    path.write_text(json.dumps(baseline))
    restored = ChainStore.from_file(path)
    assert restored.observations == {}
    export = restored.build_export([])
    assert export.collection == baseline
    assert export.item_references[remiss] == set(baseline["chains"])
    assert list(tmp_path.iterdir()) == [path]


def test_incremental_refresh_keeps_unseen_documents_and_other_chains():
    from services.chains.merge import item_references

    first = "/remisser/first/"
    second = "/remisser/second/"
    old = store_for(
        [
            {
                "name": "Remiss",
                "documents": [
                    document(first),
                    document(second),
                    document("/remisser/third/"),
                ],
            }
        ]
    )
    baseline = old.build_export([]).collection
    old_id = next(iter(baseline["chains"]))
    baseline["chains"]["unrelated"] = {
        "phases": [
            {
                "name": "Other",
                "actors": [
                    {
                        "name": "Regeringen",
                        "stages": [
                            {"type": "2099", "documents": [{"url": "/remisser/other/"}]}
                        ],
                    }
                ],
            }
        ]
    }
    fresh = store_for(
        [
            {
                "name": "Remiss",
                "documents": [
                    document(first),
                    document(second),
                    document("/remisser/z-new/"),
                ],
            }
        ]
    )
    # This new source was not among the published members. The same initial
    # anchors still identify the chain through its hash.
    fresh.baseline = deepcopy(baseline)
    before = deepcopy(fresh.baseline)
    export = fresh.build_export([])
    assert set(export.collection["chains"]) == {old_id, "unrelated"}
    assert "/remisser/z-new/" in item_references(export.collection)
    assert "/remisser/third/" in item_references(export.collection)
    assert export.collection["chains"]["unrelated"] == baseline["chains"]["unrelated"]
    assert fresh.baseline == before
    failed = ChainStore(export.collection)
    failed.observe(None, first)
    assert failed.build_export([]).collection == export.collection


def test_hash_collision_extends_only_the_new_id():
    common = "a" * 16
    identity = common + "0" * 48
    store = store_for([{"name": "Remiss", "documents": [document("/remisser/new/")]}])
    baseline: ChainCollection = {
        "chains": {
            common: {
                "phases": [
                    {
                        "name": "Sweden",
                        "actors": [
                            {
                                "name": "Regeringen",
                                "stages": [
                                    {
                                        "type": "2099",
                                        "documents": [{"url": "/remisser/old/"}],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }
    result = assign_public_ids(
        {identity: list(store.observations.values())}, baseline, []
    )
    assert result[identity] == common + "00"
    assert set(baseline["chains"]) == {common}


def test_local_backfill_writes_only_public_data_by_default_and_reports_on_request(
    monkeypatch, tmp_path
):
    from scripts import backfill_chains

    monkeypatch.chdir(tmp_path)
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/types.json").write_text('["remisser"]')
    api = tmp_path / "data/api"
    api.mkdir(parents=True)
    item = {"url": "/remisser/example/", "title": "Canonical", "types": ["2099"]}
    (api / "items.json").write_text(json.dumps([item]))
    html = '<div id="accordion--chain"><h3>Remss</h3><li class="list--DateLinkDescr__listitem"><a href="/remisser/example/">Source title</a></li></div>'
    calls = []

    class Downloader:
        b = type("Browser", (), {"close": lambda self: None})()

        def get_webpage(self, url):
            calls.append(url)
            return html

    monkeypatch.setattr(backfill_chains, "Downloader", Downloader)
    monkeypatch.setattr(backfill_chains, "report_normalizations", lambda *args: None)
    monkeypatch.setattr("sys.argv", ["backfill_chains"])
    backfill_chains.main()
    collection = (api / "chains.json").read_bytes()
    assert set(json.loads(collection)) == {"chains"}
    assert not (tmp_path / "data/.chain-state").exists()
    assert {p.name for p in api.iterdir()} == {"items.json", "chains.json"}
    items = json.loads((api / "items.json").read_text())
    assert json.loads((tmp_path / "data/remisser.json").read_text()) == items
    assert all(key in json.loads(collection)["chains"] for key in items[0]["chains"])
    reports = tmp_path / "reports"
    monkeypatch.setattr("sys.argv", ["backfill_chains", "--report-dir", str(reports)])
    backfill_chains.main()
    assert (api / "chains.json").read_bytes() == collection
    report = json.loads((reports / "chains-normalization.json").read_text())
    assert report["summary"]["normalized_stages"] == 1
    assert report["findings"][0]["before"] == "Remss"
    assert "Remss" in (reports / "chains-normalization.md").read_text()
    assert (reports / "chains-report.json").exists()
    assert {p.name for p in api.iterdir()} == {"items.json", "chains.json"}
    assert calls == [item["url"], item["url"]]
