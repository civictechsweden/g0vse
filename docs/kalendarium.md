# Calendar events

`api/kalendarium.json` is a list of calendar events, separate from the ordinary
publication pages in `api/items.json`. Each source URL is also exported as
Markdown, for example `/kalendarium/2026/10/example/` becomes
`kalendarium/2026/10/example.md`.

## Source and schema

The fetcher requests `/Filter/GetFilteredItems` with `lang=sv`,
`filterType=Taxonomy`, `filterByType=CalendarEventPage`, `filterFromToday=False`,
`displayLimited=False`, and explicit `page` / `pageSize` values. It traverses the
whole archive, not just upcoming events. The observed 2026-10-18 snapshot had
3,570 unique events from January 2023 through October 2026; these are observations,
not fixed counts or guarantees of earlier coverage.

Each JSON record contains:

| Field | Meaning |
| --- | --- |
| `url` | Original relative event URL; unique within this export |
| `title` | Event title |
| `start_date` | ISO event start date |
| `end_date` | Optional inclusive last event date |
| `participants` | Category codes listed as participants in the source |
| `summary` | Optional listing description |
| `location` | Optional location from the event detail page |
| `published`, `updated` | Optional source publication dates; unrelated to event dates |
| `categories` | Optional category codes from the detail-page footer |

Participant and category codes reference `api/codes.json`. Participants can include
both ministers and departments. The API sometimes omits former ministers who still
appear in footer categories; those categories are retained without inventing a
participant or inferring the current minister from a department. Optional fields
are absent when unavailable; `updated` is omitted when equal to `published`.
Single-day ranges with identical start and end dates omit `end_date`; a repeated
day in the listing and a single day on the detail page are treated as equivalent.
Records are sorted by start date and URL, newest first. Source URLs provide identity;
no generated IDs or additional checkpoint files are needed.

Markdown preserves event dates, participants and available body content, including
locations and links. If a new detail page is unavailable, Markdown contains the
listing information; later runs retry it. Existing detail content is retained on
failed refreshes. Publication/category metadata is exported in JSON.

## Refreshing and failures

`uv run fetch.py` refreshes the complete event listing. Detail pages are fetched
for new or changed listings, missing Markdown, records lacking publication metadata,
and events ending within the past seven days or in the future. Older unchanged
records reuse the JSON and Markdown already on the data branch. Historical
body-only edits need an explicit full refresh.

All API pages must agree on the total count and expected page sizes. Repeated URLs,
malformed event dates, incomplete fragments, zero-result responses and changes to
the first page during traversal reject the refresh and keep the previous JSON.
Other datasets can still update. Individual detail failures retain the previous
record and Markdown, or the validated listing fields for a new event. Warnings
include a count and up to five affected URLs; unavailable new details are retried.
Successful refreshes replace the calendar JSON rather than appending duplicates.
Unchanged Markdown is not rewritten. Unlisted old Markdown is not deleted.

To fetch only calendars, shared codes and calendar Markdown:

```sh
uv run python -m scripts.fetch_calendar --data-dir data
```

To refresh all historical detail pages as well:

```sh
uv run python -m scripts.fetch_calendar --data-dir data --refresh-all
```

The first backfill fetches the complete archive and its available detail pages.
The standalone command exits unsuccessfully when the listing cannot be validated.
Offline fixtures and a bounded live pagination/detail check use the existing
`pytest -m smoke` selection.
