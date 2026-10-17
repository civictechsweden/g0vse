"""Infer a limited set of missing remiss memberships from indexed shortcuts.

Rule single-study-shortcut-v1 requires one study shortcut and one official
destination chain. It never creates or merges chains, and does not publish a
remiss-to-study relationship.
"""

from copy import deepcopy
from urllib.parse import urljoin, urlsplit

from services.chains.diagnostics import FindingContext, NormalizationLog
from services.chains.enrichment_exceptions import EXCLUDED_SHORTCUTS
from services.chains.merge import item_references
from services.chains.normalization import type_from_url
from services.chains.parser import LOCAL_HOSTS, ORIGIN, ChainParseError, normalize_url
from services.chains.types import (
    ChainActor,
    ChainCollection,
    ChainItem,
    ChainStage,
    NormalizationFinding,
)

STUDY_TYPES = {"1331", "1325"}
# Rättsliga dokument is a parent category, not a competing document type.
PARENT_TYPES = {"1324"}
RULE = "single-study-shortcut-v1"


def without_inferred_memberships(collection: ChainCollection) -> ChainCollection:
    """Rebuild derived memberships from current inputs, never from past inference."""
    result = deepcopy(collection)
    for record in result["chains"].values():
        for phase in record["phases"]:
            for actor in phase["actors"]:
                for stage in actor["stages"]:
                    stage["documents"] = [
                        d for d in stage["documents"] if not d.get("inferred")
                    ]
                actor["stages"] = [s for s in actor["stages"] if s["documents"]]
            phase["actors"] = [a for a in phase["actors"] if a["stages"]]
        record["phases"] = [p for p in record["phases"] if p["actors"]]
    return result


def study_shortcuts(item: ChainItem) -> set[str] | None:
    """Keep direct study links; an unresolved local link could hide another one."""
    targets: set[str] = set()
    for shortcut in item.get("shortcuts", []):
        href = shortcut["url"]
        try:
            url = normalize_url(href, item["url"])
        except ChainParseError:
            if urlsplit(urljoin(ORIGIN + item["url"], href)).hostname in LOCAL_HOSTS:
                return None
            continue
        if type_from_url(url) in STUDY_TYPES:
            if urlsplit(href).query:
                return None
            targets.add(url)
    return targets


def destination_actor(
    collection: ChainCollection, chain_id: str, target: str, study_type: str
) -> tuple[ChainActor, int] | None:
    """Require exactly one standard domestic location for the linked study."""
    locations = []
    for phase in collection["chains"][chain_id]["phases"]:
        for actor in phase["actors"]:
            for index, stage in enumerate(actor["stages"]):
                if any(normalize_url(d["url"]) == target for d in stage["documents"]):
                    if (phase["name"], actor["name"], stage.get("type")) != (
                        "Lagstiftning i Sverige",
                        "Regeringen",
                        study_type,
                    ):
                        return None
                    locations.append((actor, index))
    if len(locations) != 1:
        return None
    actor, index = locations[0]
    if sum(s.get("type") == "2099" for s in actor["stages"]) > 1:
        return None
    return actor, index


def enrich_remiss_memberships(
    collection: ChainCollection, items: list[ChainItem], codes: dict[str, str]
) -> list[NormalizationFinding]:
    """Append inferred documents to a freshly merged official collection in place."""
    # Freeze official evidence before adding anything: no inference feeds another.
    references = item_references(collection)
    item_index = {normalize_url(item["url"]): item for item in items}
    log = NormalizationLog(item_index, codes)
    for source, item in sorted(item_index.items()):
        source_types = set(item.get("types", [])) - PARENT_TYPES
        if not source.startswith("/remisser/") or source_types != {"2099"}:
            continue
        if source in references:
            continue
        targets = study_shortcuts(item)
        if not targets or len(targets) != 1:
            continue
        target = next(iter(targets))
        if (source, target) in EXCLUDED_SHORTCUTS:
            continue
        study = item_index.get(target)
        if study is None or len(references.get(target, set())) != 1:
            continue
        study_type = type_from_url(target)
        target_types = set(study.get("types", [])) - PARENT_TYPES
        if study_type not in STUDY_TYPES or target_types != {study_type}:
            continue
        chain_id = next(iter(references[target]))
        location = destination_actor(collection, chain_id, target, study_type)
        if location is None:
            continue
        actor, study_index = location
        stage: ChainStage | None = next(
            (s for s in actor["stages"] if s.get("type") == "2099"), None
        )
        if stage is None:
            stage = {"type": "2099", "documents": []}
            actor["stages"].insert(study_index + 1, stage)
        stage["documents"].append({"url": item["url"], "inferred": True})
        log.add(
            FindingContext(chain_id, "Lagstiftning i Sverige", "Regeringen", "2099"),
            "inferred_remiss",
            None,
            chain_id,
            f"{RULE}: the sole study shortcut ({study['url']}) belongs to exactly one official chain.",
            [
                {
                    "url": item["url"],
                    "title": item.get("title"),
                    "date": None,
                    "current_page": False,
                    "sources": [item["url"]],
                }
            ],
            status="inferred",
        )
    return log.report()["findings"]
