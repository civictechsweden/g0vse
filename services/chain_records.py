"""Project reconciled views into public records, membership references and reports."""

from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass

from services.chain_parser import normalize_url
from services.chain_types import (
    Actor,
    Aliases,
    AmbiguousMatch,
    ChainCollection,
    ChainGroups,
    ChainItem,
    ChainRecord,
    ChainReport,
    Conflict,
    Document,
    Failure,
    ItemReferences,
    MembershipContext,
    Observation,
    Phase,
    PublishedDocument,
    Stage,
)


@dataclass(frozen=True)
class ChainRecords:
    collection: ChainCollection
    item_references: ItemReferences
    conflicts: list[Conflict]


def build_chain_records(
    groups: ChainGroups, aliases: Aliases, items: list[ChainItem]
) -> ChainRecords:
    local_item_urls = {normalize_url(item["url"]): item["url"] for item in items}
    item_references: ItemReferences = defaultdict(set)
    records: dict[str, ChainRecord] = {}
    conflicts: list[Conflict] = []
    for chain_id, source_views in sorted(groups.items()):
        record, chain_references, chain_conflicts = build_chain_record(
            chain_id, source_views, local_item_urls
        )
        records[chain_id] = record
        for member_url, chain_ids in chain_references.items():
            item_references[member_url].update(chain_ids)
        conflicts.extend(chain_conflicts)
    collection: ChainCollection = {
        "version": 1,
        "chains": records,
        "aliases": deepcopy(aliases),
    }
    return ChainRecords(collection, dict(item_references), conflicts)


def build_chain_record(
    chain_id: str,
    source_views: list[Observation],
    local_item_urls: dict[str, str],
) -> tuple[ChainRecord, ItemReferences, list[Conflict]]:
    phases: list[Phase[PublishedDocument]] = []
    phases_by_name: dict[str | None, Phase[PublishedDocument]] = {}
    metadata_variants: dict[MembershipContext, set[tuple[str | None, str | None]]] = (
        defaultdict(set)
    )
    conflicts: list[Conflict] = []
    item_references: ItemReferences = {}
    source_view_urls = [observation["source"] for observation in source_views]
    for observation in source_views:
        for source_phase in observation["phases"]:
            phase_name = source_phase["name"]
            if phase_name not in phases_by_name:
                phases_by_name[phase_name] = {
                    "name": phase_name,
                    "ongoing": source_phase["ongoing"],
                    "actors": [],
                }
                phases.append(phases_by_name[phase_name])
            phase = phases_by_name[phase_name]
            if phase["ongoing"] != source_phase["ongoing"]:
                conflicts.append(
                    {
                        "chain": chain_id,
                        "phase": phase_name,
                        "sources": source_view_urls,
                    }
                )
                phase["ongoing"] = None
            for source_actor in source_phase["actors"]:
                actor = find_or_add_actor(phase, source_actor["name"])
                for source_stage in source_actor["stages"]:
                    stage = find_or_add_stage(actor, source_stage["name"])
                    for document in source_stage["documents"]:
                        member_url = document["url"]
                        item_references.setdefault(member_url, set()).add(chain_id)
                        context: MembershipContext = (
                            phase_name,
                            source_actor["name"],
                            source_stage["name"],
                            member_url,
                        )
                        metadata_variants[context].add(
                            (document["title"], document["date"])
                        )
                        merge_document(
                            stage,
                            document,
                            local_item_urls.get(member_url, member_url),
                            observation["source"],
                        )
    for context, variants in metadata_variants.items():
        if len(variants) > 1:
            conflicts.append(
                {
                    "chain": chain_id,
                    "membership": list(context),
                    "sources": source_view_urls,
                }
            )
    record: ChainRecord = {
        "id": chain_id,
        "external_ids": {
            "celex": sorted({celex for view in source_views for celex in view["celex"]})
        },
        "phases": phases,
        "sources": source_view_urls,
    }
    return record, item_references, conflicts


def find_or_add_actor(
    phase: Phase[PublishedDocument], name: str | None
) -> Actor[PublishedDocument]:
    for actor in phase["actors"]:
        if actor["name"] == name:
            return actor
    actor: Actor[PublishedDocument] = {"name": name, "stages": []}
    phase["actors"].append(actor)
    return actor


def find_or_add_stage(
    actor: Actor[PublishedDocument], name: str | None
) -> Stage[PublishedDocument]:
    for stage in actor["stages"]:
        if stage["name"] == name:
            return stage
    stage: Stage[PublishedDocument] = {"name": name, "documents": []}
    actor["stages"].append(stage)
    return stage


def merge_document(
    stage: Stage[PublishedDocument],
    document: Document,
    published_url: str,
    source_view_url: str,
) -> None:
    # Same URL + different title/date remains two variants, so conflicting
    # evidence is visible. Exact matches share one document with both sources.
    for existing in stage["documents"]:
        if (existing["url"], existing["title"], existing["date"]) == (
            published_url,
            document["title"],
            document["date"],
        ):
            existing["current_page"] |= document["current_page"]
            existing["sources"] = sorted(set(existing["sources"] + [source_view_url]))
            return
    published_document: PublishedDocument = {
        **deepcopy(document),
        "url": published_url,
        "sources": [source_view_url],
    }
    stage["documents"].append(published_document)


def build_chain_report(
    records: ChainRecords,
    failures: list[Failure],
    observation_count: int,
    pending_source_views: Iterable[str] = (),
) -> ChainReport:
    ambiguous: list[AmbiguousMatch] = [
        {"url": url, "chains": sorted(chain_ids)}
        for url, chain_ids in sorted(records.item_references.items())
        if len(chain_ids) > 1
    ]
    recheck_sources = set(pending_source_views)
    recheck_sources.update(failure["source"] for failure in failures)
    recheck_sources.update(
        source for conflict in records.conflicts for source in conflict["sources"]
    )
    recheck_sources.update(
        source
        for match in ambiguous
        for chain_id in match["chains"]
        for source in records.collection["chains"][chain_id]["sources"]
    )
    return {
        "parser_failures": len(failures),
        "ambiguous_matches": len(ambiguous),
        "conflicting_observations": len(records.conflicts),
        "failures": deepcopy(failures),
        "ambiguous": ambiguous,
        "conflicts": records.conflicts,
        "recheck": sorted(recheck_sources),
        "observations": observation_count,
        "chains": len(records.collection["chains"]),
    }


def apply_item_chain_references(
    items: list[ChainItem], item_references: ItemReferences
) -> None:
    """Mutate page objects to match the memberships in a completed chain build."""
    for item in items:
        chain_ids = sorted(item_references.get(normalize_url(item["url"]), set()))
        if chain_ids:
            item["chains"] = chain_ids
        else:
            item.pop("chains", None)
