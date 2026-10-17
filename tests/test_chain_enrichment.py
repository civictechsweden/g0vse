from copy import deepcopy

import pytest

from services.chains import ChainStore
from services.chains.enrichment import without_inferred_memberships
from services.chains.records import apply_item_chain_references
from services.chains.reporting import render_normalization_report
from services.chains.types import (
    ChainCollection,
    ChainItem,
    Document,
    Observation,
    Stage,
)

SOU = "/rattsliga-dokument/statens-offentliga-utredningar/2026/08/sou-202649/"
DS = "/rattsliga-dokument/departementsserien-och-promemorior/2026/09/ds-202616/"
REMISS = "/remisser/2026/10/remiss-sou-202649/"
CHAIN = "0123456789abcdef"


@pytest.fixture
def case() -> tuple[ChainCollection, list[ChainItem]]:
    return (
        {
            "chains": {
                CHAIN: {
                    "phases": [
                        {
                            "name": "Lagstiftning i Sverige",
                            "ongoing": True,
                            "actors": [
                                {
                                    "name": "Regeringen",
                                    "stages": [
                                        {"type": "1331", "documents": [{"url": SOU}]},
                                        {
                                            "type": "1329",
                                            "documents": [{"url": "/proposition/"}],
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        },
        [
            {
                "url": SOU,
                "id": "SOU 2026:49",
                "title": "Traditionell eller rationell",
                "types": ["1324", "1331"],
                "published": "2026-08-01",
            },
            {
                "url": REMISS,
                "title": "Remiss SOU 2026:49, Traditionell eller rationell",
                "types": ["2099"],
                "senders": ["dep"],
                "published": "2026-10-15",
                "shortcuts": [
                    {"name": "SOU 2026:49 Traditionell eller rationell", "url": SOU}
                ],
            },
        ],
    )


def stages(collection):
    return collection["chains"][CHAIN]["phases"][0]["actors"][0]["stages"]


def test_adds_marked_membership_without_changing_official_data_or_inputs(case):
    baseline, items = case
    before = deepcopy(case)
    export = ChainStore(baseline).build_export(
        items, codes={"dep": "Socialdepartementet"}
    )
    assert set(export.collection["chains"]) == {CHAIN}
    assert [s["type"] for s in stages(export.collection)] == ["1331", "2099", "1329"]
    assert stages(export.collection)[1]["documents"] == [
        {"url": REMISS, "inferred": True}
    ]
    assert without_inferred_memberships(export.collection) == baseline
    assert case == before
    apply_item_chain_references(items, export.item_references)
    assert items[1]["chains"] == [CHAIN]
    (finding,) = export.normalization_report["findings"]
    assert finding["status"] == "inferred"
    assert finding["source"] == REMISS
    assert finding["departments"] == ["Socialdepartementet"]
    assert "numbered-study-shortcut-v1" in finding["reason"]
    assert export.report["recheck"] == []
    summary = render_normalization_report(export.normalization_report)
    assert "inferred: true" in summary
    assert "1** newly added" in summary


def test_ds_and_absolute_fragment_links_use_exact_indexed_item_urls(case):
    baseline, items = case
    stages(baseline)[0] = {"type": "1325", "documents": [{"url": DS}]}
    items[0].update(url=DS.rstrip("/"), id="Ds 2026:16", types=["1324", "1325"])
    items[1]["title"] = "Remiss av Ds 2026:16"
    items[1]["shortcuts"] = [
        {"name": "Promemorian", "url": "https://www.regeringen.se" + DS + "#dokument"}
    ]
    export = ChainStore(baseline).build_export(items)
    assert stages(export.collection)[1]["documents"] == [
        {"url": REMISS, "inferred": True}
    ]


@pytest.mark.parametrize(
    "change",
    [
        "no_identifier",
        "identifier_mismatch",
        "multiple_identifiers",
        "label_mismatch",
        "no_study_identifier",
        "type_mismatch",
        "source_type_conflict",
        "target_type_conflict",
        "not_a_remiss",
        "another_study",
        "unindexed_study",
        "legacy_link",
        "selector",
        "multiple_chains",
        "nonstandard_actor",
        "duplicate_study_stage",
        "duplicate_remiss_stage",
    ],
)
def test_uncertain_candidates_leave_the_collection_unchanged(case, change):
    baseline, items = case
    remiss = items[1]
    if change == "no_identifier":
        remiss["title"] = "Remiss av Traditionell eller rationell"
    elif change == "identifier_mismatch":
        remiss["title"] = "Remiss SOU 2025:49"
    elif change == "multiple_identifiers":
        remiss["title"] = "Remiss SOU 2026:49 och SOU 2026:50"
    elif change == "label_mismatch":
        remiss["shortcuts"][0]["name"] = "SOU 2025:49"
    elif change == "no_study_identifier":
        items[0].pop("id")
    elif change == "type_mismatch":
        items[0]["types"] = ["1325"]
    elif change == "source_type_conflict":
        remiss["types"].append("1334")
    elif change == "target_type_conflict":
        items[0]["types"].append("1342")
    elif change == "not_a_remiss":
        remiss["types"] = ["1334"]
    elif change == "another_study":
        remiss["shortcuts"].append({"name": "Background", "url": DS})
    elif change == "unindexed_study":
        items.pop(0)
    elif change == "legacy_link":
        remiss["shortcuts"].append(
            {"name": "Another document", "url": "/link/unknown.aspx"}
        )
    elif change == "selector":
        remiss["shortcuts"][0]["url"] += "?id=other-process"
    elif change == "multiple_chains":
        baseline["chains"]["other"] = deepcopy(baseline["chains"][CHAIN])
    elif change == "nonstandard_actor":
        baseline["chains"][CHAIN]["phases"][0]["actors"][0]["name"] = "Another actor"
    elif change == "duplicate_study_stage":
        stages(baseline).append(deepcopy(stages(baseline)[0]))
    elif change == "duplicate_remiss_stage":
        stages(baseline).extend(
            [
                {"type": "2099", "documents": [{"url": "/remisser/first/"}]},
                {"type": "2099", "documents": [{"url": "/remisser/second/"}]},
            ]
        )
    export = ChainStore(baseline).build_export(items)
    assert export.collection == baseline
    assert export.normalization_report["findings"] == []


def test_does_not_move_an_existing_official_remiss_between_chains(case):
    baseline, items = case
    baseline["chains"]["other"] = {
        "phases": [
            {
                "name": "Lagstiftning i Sverige",
                "actors": [
                    {
                        "name": "Regeringen",
                        "stages": [
                            {"type": "2099", "documents": [{"url": REMISS}]},
                        ],
                    }
                ],
            }
        ]
    }
    export = ChainStore(baseline).build_export(items)
    assert export.collection == baseline
    assert export.item_references[REMISS] == {"other"}


def test_rebuild_is_deterministic_reuses_stage_and_keeps_distinct_findings(case):
    baseline, items = case
    stages(baseline).insert(
        1, {"type": "2099", "documents": [{"url": "/remisser/official/"}]}
    )
    second = deepcopy(items[1])
    second["url"] = "/remisser/2026/10/another-consultation/"
    items.append(second)
    first = ChainStore(baseline).build_export(items)
    restored = ChainStore(first.collection).build_export(list(reversed(items)))
    assert restored.collection == first.collection
    assert len(stages(first.collection)) == 3
    assert stages(first.collection)[1]["documents"][0] == {"url": "/remisser/official/"}
    assert len(first.normalization_report["findings"]) == 2
    assert first.normalization_report["summary"]["new_inferred_remisses"] == 2
    assert restored.normalization_report["summary"]["new_inferred_remisses"] == 0
    assert restored.report["recheck"] == []


@pytest.mark.parametrize(
    "change", ["shortcut_removed", "ambiguous_target", "item_removed"]
)
def test_retracts_unsupported_inference_and_prunes_its_empty_stage(case, change):
    baseline, items = case
    inferred = ChainStore(baseline).build_export(items).collection
    if change == "shortcut_removed":
        items[1]["shortcuts"] = []
    elif change == "ambiguous_target":
        inferred["chains"]["other"] = deepcopy(baseline["chains"][CHAIN])
        baseline["chains"]["other"] = deepcopy(baseline["chains"][CHAIN])
    else:
        items.pop()
    assert ChainStore(inferred).build_export(items).collection == baseline


def official_view(include_remiss: bool) -> Observation:
    documents: list[Stage[Document]] = [
        {
            "name": "Statens offentliga utredningar",
            "documents": [
                {
                    "url": SOU,
                    "title": "Traditionell eller rationell",
                    "date": "2026-08-01",
                    "current_page": True,
                },
            ],
        }
    ]
    if include_remiss:
        documents.append(
            {
                "name": "Remiss",
                "documents": [
                    {
                        "url": REMISS,
                        "title": "Remiss SOU 2026:49",
                        "date": "2026-10-15",
                        "current_page": False,
                    },
                ],
            }
        )
    return {
        "source": SOU,
        "item_url": SOU,
        "parser_version": 1,
        "content_hash": "test",
        "celex": [],
        "phases": [
            {
                "name": "Lagstiftning i Sverige",
                "ongoing": True,
                "actors": [{"name": "Regeringen", "stages": documents}],
            }
        ],
    }


def test_official_confirmation_removes_marker_and_inference_finding(case):
    baseline, items = case
    stages(baseline).pop()
    store = ChainStore(baseline)
    store.baseline = store.build_export(items).collection
    store.observations[SOU] = official_view(include_remiss=True)
    export = store.build_export(items)
    assert set(export.collection["chains"]) == {CHAIN}
    remiss_stage = next(s for s in stages(export.collection) if s["type"] == "2099")
    assert remiss_stage["documents"] == [{"url": REMISS}]
    assert not any(
        f["kind"] == "inferred_remiss" for f in export.normalization_report["findings"]
    )


def test_inferred_members_never_become_identity_anchors(case):
    baseline, items = case
    # A sole official member can grow while keeping its key. An earlier inferred
    # member must not turn it into a two-anchor chain and prevent that match.
    stages(baseline).pop()
    inferred = ChainStore(baseline).build_export(items).collection
    items[1]["published"] = "1900-01-01"
    view = official_view(include_remiss=False)
    view["phases"][0]["actors"][0]["stages"].append(
        {
            "name": "Proposition",
            "documents": [
                {
                    "url": "/new-proposition/",
                    "title": "New",
                    "date": "2026-10-16",
                    "current_page": False,
                },
            ],
        }
    )
    store = ChainStore(inferred)
    store.observations[SOU] = view
    export = store.build_export(items)
    assert set(export.collection["chains"]) == {CHAIN}
    assert export.item_references[REMISS] == {CHAIN}


def test_inferred_study_cannot_seed_another_inference(case):
    baseline, items = case
    stages(baseline)[0]["documents"][0]["inferred"] = True
    export = ChainStore(baseline).build_export(items)
    assert REMISS not in export.item_references
