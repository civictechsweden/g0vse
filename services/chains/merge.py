"""Apply fresh chain views without discarding untouched published memberships."""

from copy import deepcopy

from services.chains.parser import normalize_url
from services.chains.types import (
    ChainCollection,
    ChainRecord,
    ChainStage,
    ItemReferences,
)


def merge_stages(old: list[ChainStage], fresh: list[ChainStage]) -> list[ChainStage]:
    remaining = deepcopy(old)
    result = []
    for stage in fresh:
        updated = deepcopy(stage)
        key = (stage.get("type"), stage.get("name"))
        match = next(
            (
                i
                for i, s in enumerate(remaining)
                if (s.get("type"), s.get("name")) == key
            ),
            None,
        )
        if match is not None:
            previous = remaining.pop(match)
            refreshed = {normalize_url(d["url"]) for d in stage["documents"]}
            updated["documents"].extend(
                d
                for d in previous["documents"]
                if normalize_url(d["url"]) not in refreshed
            )
        result.append(updated)
    return result + remaining


def merge_record(old: ChainRecord, fresh: ChainRecord) -> ChainRecord:
    result = deepcopy(fresh)
    old_phases = {p["name"]: p for p in old["phases"]}
    for phase in result["phases"]:
        previous = old_phases.pop(phase["name"], None)
        if previous is None:
            continue
        old_actors = {a["name"]: a for a in previous["actors"]}
        for actor in phase["actors"]:
            old_actor = old_actors.pop(actor["name"], None)
            if old_actor is not None:
                actor["stages"] = merge_stages(old_actor["stages"], actor["stages"])
        phase["actors"].extend(old_actors.values())
    result["phases"].extend(old_phases.values())
    return result


def merge_collections(
    baseline: ChainCollection, fresh: ChainCollection
) -> ChainCollection:
    chains = deepcopy(baseline["chains"])
    for key, record in fresh["chains"].items():
        chains[key] = (
            merge_record(chains[key], record) if key in chains else deepcopy(record)
        )
    return {"chains": dict(sorted(chains.items()))}


def item_references(collection: ChainCollection) -> ItemReferences:
    references: ItemReferences = {}
    for key, record in collection["chains"].items():
        for phase in record["phases"]:
            for actor in phase["actors"]:
                for stage in actor["stages"]:
                    for document in stage["documents"]:
                        references.setdefault(
                            normalize_url(document["url"]), set()
                        ).add(key)
    return references
