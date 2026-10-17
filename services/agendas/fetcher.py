"""Build a complete replacement snapshot before publishing any agenda records."""

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from urllib.parse import urlencode

from services.agendas.parser import (
    LISTING,
    ORIGIN,
    AgendaError,
    clean,
    listing_root,
    parse_fragment,
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
            raise AgendaError("CasePage total changed or the global listing is empty")
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
    if downloader.b.get_json(query_url(root, 1, page_size)) != first_response:
        raise AgendaError("CasePage first page changed during pagination")
    return result


def fetch_agendas(
    downloader, codes: dict[str, str], *, page_size: int = 1000
) -> AgendaExport:
    """The complete CasePage traversal is mandatory; missing source dates stay null."""
    try:
        html = downloader.get_webpage(LISTING)
        if not html:
            raise AgendaError("Could not fetch the regeringsärenden listing")
        root, labels = listing_root(html)
        records = read_results(downloader, root, page_size)
        by_source = defaultdict(list)
        for record in records:
            by_source[record["source"]].append(record)
        pages, undated = {}, []
        for index, (source, entries) in enumerate(sorted(by_source.items()), 1):
            page = downloader.get_webpage(source)
            if not page:
                raise AgendaError(f"Could not fetch weekly agenda {source}")
            context, page_labels = weekly_context(
                page, source, entries[0]["year"], entries[0]["week"]
            )
            labels.update(page_labels)
            apply_weekly_context(entries, context)
            if any(entry["meeting_date"] is None for entry in entries):
                undated.append(source)
            if context:
                pages[source] = page
            if index % 20 == 0 or index == len(by_source):
                print(
                    f"Regeringsärenden: read weekly metadata {index}/{len(by_source)}.",
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
        return AgendaExport(records, labels, pages, undated)
    except AgendaError:
        raise
    except Exception as error:
        raise AgendaError(f"Could not build regeringsärenden: {error}") from error
