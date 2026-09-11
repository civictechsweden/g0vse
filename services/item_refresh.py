from collections import defaultdict
from dataclasses import dataclass, field

# These fields come from regeringen.se's search results. Everything else is
# parsed from the document page and should survive an incremental refresh.
SEARCH_ITEM_FIELDS = {
    "title",
    "url",
    "published",
    "updated",
    "types",
    "senders",
    "summary",
}


@dataclass
class RefreshPlan:
    """Information needed to refresh pages without reordering them first."""

    candidate_order: list[str] = field(default_factory=list)
    force_refresh_urls: set[str] = field(default_factory=set)
    new_urls: set[str] = field(default_factory=set)
    previous_items: dict[str, dict] = field(default_factory=dict)


def merge_search_metadata(stored_item, fresh_item):
    """Update search fields while retaining metadata parsed from the page."""
    merged_item = stored_item.copy()
    for name in SEARCH_ITEM_FIELDS:
        if name in fresh_item:
            merged_item[name] = fresh_item[name]
        else:
            merged_item.pop(name, None)
    return merged_item


def plan_incremental_refresh(stored_items, refresh_candidates):
    """Merge candidates into stored items without changing existing order."""
    candidates_by_url = {item["url"]: item for item in refresh_candidates}
    stored_urls = {item["url"] for item in stored_items}

    previous_items: dict[str, dict] = {}
    merged_items = []
    for stored_item in stored_items:
        url = stored_item["url"]
        fresh_item = candidates_by_url.get(url)
        if fresh_item is None:
            merged_items.append(stored_item)
            continue

        # Keep the complete old object so a failed request cannot replace it
        # with the smaller object returned by the search endpoint.
        previous_items.setdefault(url, stored_item)
        merged_items.append(merge_search_metadata(stored_item, fresh_item))

    new_items = [item for item in refresh_candidates if item["url"] not in stored_urls]
    candidate_order = list(dict.fromkeys(item["url"] for item in refresh_candidates))

    plan = RefreshPlan(
        candidate_order=candidate_order,
        force_refresh_urls=set(candidate_order),
        new_urls={item["url"] for item in new_items},
        previous_items=previous_items,
    )
    return new_items + merged_items, plan


def promote_changed_items(items, candidate_order, changed_urls):
    """Move changed candidates to the front and leave all others in place."""
    if not changed_urls:
        return items

    changed_by_url = defaultdict(list)
    unchanged_items = []
    for item in items:
        if item["url"] in changed_urls:
            changed_by_url[item["url"]].append(item)
        else:
            unchanged_items.append(item)

    changed_items = []
    for url in candidate_order:
        changed_items.extend(changed_by_url.pop(url, []))

    # Defensive fallback: changed URLs should normally all be candidates.
    for grouped_items in changed_by_url.values():
        changed_items.extend(grouped_items)

    return changed_items + unchanged_items
