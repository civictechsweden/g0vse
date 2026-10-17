"""Group current observations and match them to the published collection."""

import re
from collections import defaultdict
from collections.abc import Iterable

from services.chains.parser import digest, memberships, normalize_url
from services.chains.types import (
    ChainCollection,
    ChainGroups,
    ChainItem,
    ChainRecord,
    Observation,
    PublicIds,
)


def observation_identity(observation: Observation) -> list[str | list[str]]:
    celex = sorted(observation.get("identity_celex", observation["celex"]))
    if celex:
        return ["celex", celex]
    dates: dict[str, str] = {}
    for _, _, _, document in memberships(observation):
        url = document["url"]
        dates[url] = min(document["date"] or "9999", dates.get(url, "9999"))
    ordered = sorted(dates, key=lambda url: (dates[url], url))
    if len(ordered) < 2:
        return ["source", observation["source"]]
    return ["members", ordered[:2]]


def reconcile_identities(observations: dict[str, Observation]) -> ChainGroups:
    groups: ChainGroups = defaultdict(list)
    for _, observation in sorted(observations.items()):
        if any(memberships(observation)):
            groups[digest(observation_identity(observation))].append(observation)
    return dict(sorted(groups.items()))


def member_urls(record: ChainRecord) -> set[str]:
    return {
        normalize_url(document["url"])
        for phase in record["phases"]
        for actor in phase["actors"]
        for stage in actor["stages"]
        for document in stage["documents"]
    }


def proposal_ids(record: ChainRecord) -> tuple[str, ...]:
    phases = record["phases"]
    if not phases or "inom EU" not in (phases[0]["name"] or ""):
        return ()
    return tuple(
        sorted(
            {
                celex
                for actor in phases[0]["actors"]
                for stage in actor["stages"]
                for document in stage["documents"]
                if "eur-lex.europa.eu" in document["url"]
                for celex in re.findall(
                    r"\b[0-9]{5}[A-Z]{1,2}[0-9]{4}\b", document["url"]
                )
            }
        )
    )


def assign_public_ids(
    groups: ChainGroups, baseline: ChainCollection, items: Iterable[ChainItem]
) -> PublicIds:
    """Keep an unambiguous published ID; otherwise allocate a hash prefix.

    A refreshed source must belong to the old chain and share both old anchors.
    CELEX bundles must match exactly. One shared member never combines unrelated
    processes. No merge/split history or ID registry is persisted.
    """
    item_index = {normalize_url(item["url"]): item for item in items}
    urls = {key: member_urls(record) for key, record in baseline["chains"].items()}
    proposals = {
        key: proposal_ids(record) for key, record in baseline["chains"].items()
    }
    by_member: dict[str, set[str]] = defaultdict(set)
    anchors = {}
    for key, record in baseline["chains"].items():
        dates = {}
        for phase in record["phases"]:
            for actor in phase["actors"]:
                for stage in actor["stages"]:
                    for document in stage["documents"]:
                        url = normalize_url(document["url"])
                        date = (
                            document.get("date")
                            or item_index.get(url, {}).get("published")
                            or "9999"
                        )
                        dates[url] = min(date, dates.get(url, "9999"))
                        by_member[url].add(key)
        anchors[key] = set(sorted(dates, key=lambda url: (dates[url], url))[:2])
    used = set(baseline["chains"])
    claimed = set()
    result = {}
    existing_keys = sorted(urls, key=lambda key: (-len(key), key))
    for identity, observations in sorted(groups.items()):
        members = {
            normalize_url(d["url"]) for o in observations for *_, d in memberships(o)
        }
        celex = tuple(
            sorted(observations[0].get("identity_celex", observations[0]["celex"]))
        )
        candidates = set()
        for observation in observations:
            source = normalize_url(observation["source"])
            for key in by_member.get(source, set()):
                if key in claimed or proposals[key] != celex:
                    continue
                if celex or (len(anchors[key]) == 2 and anchors[key] <= members):
                    candidates.add(key)
                elif urls[key] == {source} and source in members:
                    candidates.add(key)
        # Exact hashes also match when the refreshed view is hosted on a newly
        # added member, rather than a previously published source page.
        for key in existing_keys:
            if identity.startswith(key) and key not in claimed:
                if len(urls[key] & members) >= min(2, len(members)):
                    candidates = {key}
                    break
        if len(candidates) == 1:
            key = candidates.pop()
            claimed.add(key)
        else:
            length = 16
            while identity[:length] in used:
                length += 2
                if length > len(identity):
                    raise ValueError("Cannot allocate a unique chain ID")
            key = identity[:length]
            used.add(key)
        result[identity] = key
    return result
