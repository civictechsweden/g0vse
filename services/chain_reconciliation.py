"""Choose chain IDs and resolve historical aliases without changing stored state."""

from collections import defaultdict
from dataclasses import dataclass

from services.chain_parser import digest, memberships
from services.chain_types import Aliases, Assignments, ChainGroups, Observation


@dataclass(frozen=True)
class Reconciliation:
    groups: ChainGroups
    assignments: Assignments
    aliases: Aliases


def observation_identity(observation: Observation) -> list[str | list[str]]:
    celex = observation.get("identity_celex", observation["celex"])
    if celex:
        return ["celex", celex]
    earliest_dates: dict[str, str] = {}
    for _, _, _, document in memberships(observation):
        member_url = document["url"]
        date = document["date"] or "9999"
        earliest_dates[member_url] = min(date, earliest_dates.get(member_url, date))
    ordered_members = sorted(earliest_dates, key=lambda url: (earliest_dates[url], url))
    # /a/ alone could occur in unrelated chains. Two anchors provide evidence
    # to combine views; a singleton therefore uses its source view as identity.
    if len(ordered_members) < 2:
        return ["source", observation["source"]]
    return ["members", ordered_members[:2]]


def reconcile_identities(
    observations: dict[str, Observation],
    previous_assignments: Assignments,
    previous_aliases: Aliases,
) -> Reconciliation:
    views_by_initial_id: dict[str, list[Observation]] = defaultdict(list)
    for _, observation in sorted(observations.items()):
        if any(memberships(observation)):
            initial_id = "chain-" + digest(observation_identity(observation))
            views_by_initial_id[initial_id].append(observation)

    successors_by_previous_id: dict[str, set[str]] = defaultdict(set)
    for initial_id, source_views in views_by_initial_id.items():
        for observation in source_views:
            source_view_url = observation["source"]
            if source_view_url in previous_assignments:
                previous_id = previous_assignments[source_view_url]
                successors_by_previous_id[previous_id].add(initial_id)

    groups: ChainGroups = {}
    assignments: Assignments = {}
    used_ids: set[str] = set()
    for initial_id, source_views in sorted(views_by_initial_id.items()):
        # Split: if old A now has successors X and Y, only min(X, Y) can
        # retain A. Merge: choose the smallest eligible old ID, alias the rest.
        eligible_previous_ids = sorted(
            {
                previous_assignments[observation["source"]]
                for observation in source_views
                if observation["source"] in previous_assignments
                and initial_id
                == min(
                    successors_by_previous_id[
                        previous_assignments[observation["source"]]
                    ]
                )
            }
            - used_ids
        )
        published_id = eligible_previous_ids[0] if eligible_previous_ids else initial_id
        if published_id in used_ids:
            published_id = "chain-" + digest(
                [initial_id, [observation["source"] for observation in source_views]]
            )
        used_ids.add(published_id)
        groups[published_id] = source_views
        for observation in source_views:
            assignments[observation["source"]] = published_id

    aliases = resolve_aliases(
        previous_assignments, assignments, previous_aliases, groups
    )
    return Reconciliation(groups, assignments, aliases)


def resolve_aliases(
    previous_assignments: Assignments,
    assignments: Assignments,
    previous_aliases: Aliases,
    live_groups: ChainGroups,
) -> Aliases:
    replacements: dict[str, set[str]] = defaultdict(set)
    for source_view_url, previous_id in previous_assignments.items():
        if source_view_url in assignments:
            replacements[previous_id].add(assignments[source_view_url])
    aliases = {chain_id: set(targets) for chain_id, targets in previous_aliases.items()}
    for previous_id, successors in replacements.items():
        if successors != {previous_id}:
            aliases[previous_id] = successors

    def live_targets(chain_id: str, visited: set[str]) -> set[str]:
        if chain_id in visited:
            return set()
        targets = {chain_id} if chain_id in live_groups else set()
        for target in aliases.get(chain_id, set()) - {chain_id}:
            targets.update(live_targets(target, visited | {chain_id}))
        return targets

    # A -> B -> C becomes A -> C. A split A -> [A, D] deliberately retains
    # A in its own successor list: clients must consult aliases for live IDs too.
    public_aliases: Aliases = {}
    for previous_id in sorted(aliases):
        targets = sorted(live_targets(previous_id, set()))
        if targets and targets != [previous_id]:
            public_aliases[previous_id] = targets
    return public_aliases
