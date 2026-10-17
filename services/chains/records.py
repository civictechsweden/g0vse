"""Project reconciled views into public records, membership references and reports."""

from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass

from services.chains.normalization import stage_type_from_name
from services.chains.parser import normalize_url
from services.chains.types import (
    Actor,
    AmbiguousMatch,
    ChainActor,
    ChainCollection,
    ChainDocument,
    ChainGroups,
    ChainItem,
    ChainPhase,
    ChainRecord,
    ChainReport,
    ChainStage,
    Conflict,
    Document,
    Failure,
    ItemReferences,
    MembershipContext,
    Observation,
    Phase,
    PublicIds,
    PublishedDocument,
    Stage,
)


@dataclass(frozen=True)
class ChainRecords:
    collection: ChainCollection
    item_references: ItemReferences
    conflicts: list[Conflict]
    sources: dict[str, list[str]]
    evidence: dict[str, list[Phase[PublishedDocument]]]


def build_chain_records(
    groups: ChainGroups, items: list[ChainItem], public_ids: PublicIds
) -> ChainRecords:
    item_index = {normalize_url(item["url"]): item for item in items}
    item_references: ItemReferences = defaultdict(set)
    records: dict[str, ChainRecord] = {}
    conflicts: list[Conflict] = []
    sources: dict[str, list[str]] = {}
    evidence: dict[str, list[Phase[PublishedDocument]]] = {}
    published_groups: dict[str, list[Observation]] = defaultdict(list)
    for chain_id, source_views in sorted(groups.items()):
        published_groups[public_ids[chain_id]].extend(source_views)
    for public_id, source_views in sorted(published_groups.items()):
        source_views = sorted(source_views, key=lambda view: view["source"])
        record, chain_references, chain_conflicts, phases = build_chain_record(
            public_id, source_views, item_index
        )
        records[public_id] = record
        sources[public_id] = [view["source"] for view in source_views]
        evidence[public_id] = phases
        for member_url, chain_ids in chain_references.items():
            item_references[member_url].update(chain_ids)
        conflicts.extend(chain_conflicts)
    collection: ChainCollection = {
        "chains": dict(sorted(records.items())),
    }
    return ChainRecords(collection, dict(item_references), conflicts, sources, evidence)


def build_chain_record(
    chain_id: str,
    source_views: list[Observation],
    item_index: dict[str, ChainItem],
) -> tuple[ChainRecord, ItemReferences, list[Conflict], list[Phase[PublishedDocument]]]:
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
                            item_index[member_url]["url"]
                            if member_url in item_index
                            else member_url,
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
    # Empty source scaffolding has no public membership. Keep evidence aligned
    # with the public arrays so normalization can inspect the original labels.
    for phase in phases:
        for actor in phase["actors"]:
            actor["stages"] = [s for s in actor["stages"] if s["documents"]]
        phase["actors"] = [a for a in phase["actors"] if a["stages"]]
    phases = [p for p in phases if p["actors"]]
    record: ChainRecord = {"phases": [assemble_phase(p, item_index) for p in phases]}
    return record, item_references, conflicts, phases


# These are the type keys already agreed in chains.draft.json. Additional URL
# types are applied explicitly by the subsequent normalization, with a finding.
DRAFT_STAGE_TYPES = {
    "1325",
    "1327",
    "1329",
    "1330",
    "1331",
    "2085",
    "2099",
    "1341",
    "1342",
    "riksdagsbeslut",
    "sfs",
    "eu-direktiv",
    "eu-forordning",
}


def assemble_phase(
    phase: Phase[PublishedDocument], item_index: dict[str, ChainItem]
) -> ChainPhase:
    result: ChainPhase = {"name": phase["name"], "actors": []}
    if phase["ongoing"] is not None:
        result["ongoing"] = phase["ongoing"]
    for actor in phase["actors"]:
        public_actor: ChainActor = {"name": actor["name"], "stages": []}
        for stage in actor["stages"]:
            public_stage: ChainStage = {"documents": []}
            stage_type = stage_type_from_name(stage["name"])
            if stage_type in DRAFT_STAGE_TYPES:
                public_stage["type"] = stage_type
            elif stage["name"]:
                public_stage["name"] = stage["name"]
            seen = set()
            for document in stage["documents"]:
                item = item_index.get(normalize_url(document["url"]))
                public_document: ChainDocument = {"url": document["url"]}
                if item is None or not item.get("title"):
                    public_document["title"] = document["title"]
                date = document["date"]
                if date and (
                    not item or date[:10] != (item.get("published") or "")[:10]
                ):
                    public_document["date"] = date
                key = (
                    public_document["url"],
                    public_document.get("title"),
                    public_document.get("date"),
                )
                if key not in seen:
                    seen.add(key)
                    public_stage["documents"].append(public_document)
            public_actor["stages"].append(public_stage)
        result["actors"].append(public_actor)
    return result


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
        for source in records.sources.get(chain_id, [])
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
