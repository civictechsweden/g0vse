"""Refresh the two newest weekly agendas while retaining stored history."""

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from urllib.parse import urlencode

from services.agendas.parser import (
    ORIGIN,
    WEEKLY_LISTING,
    AgendaError,
    clean,
    listing_root,
    parse_fragment,
    recent_weekly_sources,
    weekly_context,
)


@dataclass
class AgendaExport:
    records: list[dict]
    labels: dict[str, str]
    pages: dict[str, str]
    undated_sources: list[str]


def query_url(root: str, page: int, page_size: int = 1000) -> str:
    return (
        ORIGIN
        + "/Filter/GetFilteredItems?"
        + urlencode(
            {
                "lang": "sv",
                "filterType": "Structure",
                "filterByType": "CasePage",
                "rootPageReference": root,
                "page": page,
                "pageSize": page_size,
                "displayLimited": "False",
                "sortAlphabetically": "False",
                "filterFromToday": "False",
            }
        )
    )


def fingerprint(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)


def context_key(record: dict) -> str:
    # The API can omit a former minister whose name is still in the weekly h4.
    return fingerprint(
        {k: v for k, v in record.items() if k not in {"meeting_date", "minister"}}
    )


def apply_weekly_context(entries: list[dict], context: list[dict]) -> None:
    """Verify the full weekly body, then enrich only unambiguous source metadata."""
    if context and Counter(map(context_key, context)) != Counter(
        map(context_key, entries)
    ):
        raise AgendaError(
            f"Weekly agenda and API entries disagree on {entries[0]['source']}"
        )
    index = defaultdict(list)
    for row in context:
        index[context_key(row)].append(row)
    for entry in entries:
        candidates = index[context_key(entry)]
        if entry["minister"]:
            candidates = [
                r for r in candidates if r["minister"] in {None, entry["minister"]}
            ]
            if context and not candidates:
                raise AgendaError(
                    f"Weekly minister and API disagree on {entry['source']}"
                )
        ministers = {r["minister"] for r in candidates if r["minister"]}
        if entry["minister"] is None and len(ministers) == 1:
            entry["minister"] = next(iter(ministers))
        dates = {r["meeting_date"] for r in candidates if r["meeting_date"]}
        entry["meeting_date"] = next(iter(dates)) if len(dates) == 1 else None


def read_results(downloader, root: str, page_size: int) -> list[dict]:
    if page_size < 1:
        raise AgendaError("page_size must be positive")
    result, seen = [], set()
    page, expected_total = 1, None
    first_response = None
    while True:
        response = downloader.b.get_json(query_url(root, page, page_size))
        total, records = parse_fragment(response)
        if expected_total is None:
            expected_total, first_response = total, response
        if total != expected_total or total == 0:
            raise AgendaError("CasePage total changed or the listing is empty")
        expected_size = min(page_size, total - len(result))
        if len(records) != expected_size:
            raise AgendaError(
                f"Incomplete CasePage results on page {page}: {len(records)}/{expected_size}"
            )
        for record in records:
            key = fingerprint(record)
            if key in seen:
                raise AgendaError(f"Repeated CasePage entry on page {page}")
            seen.add(key)
        result.extend(records)
        if len(result) == total:
            break
        page += 1
    # Detect insertions/removals or shifts while traversing a changing listing.
    if (
        page > 1
        and downloader.b.get_json(query_url(root, 1, page_size)) != first_response
    ):
        raise AgendaError("CasePage first page changed during pagination")
    return result


def fetch_agendas(
    downloader,
    codes: dict[str, str],
    *,
    page_size: int = 1000,
    previous_records: list[dict] | None = None,
) -> AgendaExport:
    """Replace complete recent weeks; leave older records and Markdown untouched."""
    try:
        html = downloader.get_webpage(WEEKLY_LISTING)
        if not html:
            raise AgendaError("Could not fetch the weekly publication listing")
        sources = recent_weekly_sources(html)
        records, pages, labels = [], {}, {}
        for index, (source, year, week) in enumerate(sources, 1):
            page = downloader.get_webpage(source)
            if not page:
                raise AgendaError(f"Could not fetch weekly agenda {source}")
            root, page_labels = listing_root(page)
            labels.update(page_labels)
            entries = read_results(downloader, root, page_size)
            if any(
                (row["source"], row["year"], row["week"]) != (source, year, week)
                for row in entries
            ):
                raise AgendaError(f"CasePage results do not belong to {source}")
            context, _ = weekly_context(page, source, year, week)
            apply_weekly_context(entries, context)
            records.extend(entries)
            if context:
                pages[source] = page
            print(
                f"Regeringsärenden: refreshed week {index}/{len(sources)} "
                f"({len(entries):,} entries) from {source}.",
                flush=True,
            )
        name_codes = defaultdict(set)
        for code, name in (codes | labels).items():
            name_codes[clean(name)].add(code)
        for record in records:
            for field in ("department", "minister"):
                matches = name_codes.get(record[field], set())
                if len(matches) == 1:
                    record[field + "_code"] = next(iter(matches))
        refreshed_sources = {source for source, _, _ in sources}
        records.extend(
            row
            for row in previous_records or []
            if row["source"] not in refreshed_sources
        )
        records.sort(
            key=lambda r: (
                -r["year"],
                -r["week"],
                r["source"],
                r["department"],
                r["minister"] or "",
                r["agenda_number"] or "",
                fingerprint(r),
            )
        )
        undated = sorted(
            {row["source"] for row in records if row.get("meeting_date") is None}
        )
        return AgendaExport(records, labels, pages, undated)
    except AgendaError:
        raise
    except Exception as error:
        raise AgendaError(f"Could not build regeringsärenden: {error}") from error
