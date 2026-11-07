"""Read a complete event listing before refreshing new and recent details."""

from datetime import date, timedelta
from urllib.parse import urlencode

from services.calendar.parser import (
    ORIGIN,
    CalendarError,
    parse_detail,
    parse_fragment,
    render_markdown,
    signature,
)


def query_url(page=1, page_size=1000):
    return (
        ORIGIN
        + "/Filter/GetFilteredItems?"
        + urlencode(
            {
                "lang": "sv",
                "filterType": "Taxonomy",
                "filterByType": "CalendarEventPage",
                "filterFromToday": "False",
                "displayLimited": "False",
                "page": page,
                "pageSize": page_size,
            }
        )
    )


def fetch_listing(downloader, page_size=1000):
    if page_size < 1:
        raise CalendarError("page_size must be positive")
    records, labels, seen = [], {}, set()
    page, total, first = 1, None, None
    while True:
        count, rows, names = parse_fragment(
            downloader.b.get_json(query_url(page, page_size))
        )
        if total is None:
            total, first = count, rows
        if (
            not total
            or count != total
            or len(rows) != min(page_size, total - len(records))
        ):
            raise CalendarError(f"Incomplete calendar listing on page {page}")
        for row in rows:
            if row["url"] in seen:
                raise CalendarError(f"Repeated calendar event: {row['url']}")
            seen.add(row["url"])
        records.extend(rows)
        labels.update(names)
        if len(records) == total:
            break
        page += 1
    check_count, check_rows, _ = parse_fragment(
        downloader.b.get_json(query_url(1, page_size))
    )
    if check_count != total or sorted(check_rows, key=lambda r: r["url"]) != sorted(
        first or [], key=lambda r: r["url"]
    ):
        raise CalendarError("Calendar listing changed during pagination")
    return sorted(
        records, key=lambda r: (r["start_date"], r["url"]), reverse=True
    ), labels


def refresh_details(
    downloader, records, labels, previous, root, *, force=False, today=None
):
    since = ((today or date.today()) - timedelta(days=7)).isoformat()
    result, markdown, failures = [], {}, []
    fetched = 0
    for row in records:
        old = previous.get(row["url"])
        path = root / (row["url"].strip("/") + ".md")
        recent = row.get("end_date", row["start_date"]) >= since
        if (
            not force
            and old
            and old.get("published")
            and path.exists()
            and signature(old) == row
            and not recent
        ):
            result.append(old)
            continue
        fetched += 1
        try:
            html = downloader.get_webpage(row["url"])
            if not html:
                raise CalendarError("Could not download event detail")
            details, names, content = parse_detail(html, row)
            labels.update(names)
            result.append(row | details)
            markdown[row["url"]] = content
        except Exception as error:
            failures.append((row["url"], str(error)))
            result.append(old if old is not None else row)
            if not path.exists():
                markdown[row["url"]] = render_markdown(old or row, labels)
        if fetched % 100 == 0:
            print(f"Calendar: fetched {fetched:,} event detail pages.", flush=True)
    result.sort(key=lambda r: (r["start_date"], r["url"]), reverse=True)
    return result, markdown, failures, fetched
