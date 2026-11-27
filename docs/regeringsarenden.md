# Regeringsärenden

Weekly pages describe planned agenda items, not proof that a decision was taken.
Individual entries are separate from the weekly page objects in `regeringsarenden.json`.

## Observed source contract

Captured in a headless Camoufox browser on 2026-10-17, on both
[the global listing](https://www.regeringen.se/regeringsarenden/) and
[week 42, 2026](https://www.regeringen.se/regeringsarenden/regeringsarenden-vecka-42-2026/).
The browser performs GET requests to `/Filter/GetFilteredItems` with:

| Parameter | Observed value |
| --- | --- |
| `lang` | `sv` |
| `filterType` | `Structure` |
| `filterByType` | `CasePage` |
| `rootPageReference` | `548462` globally; `664600` for that weekly page |
| `page` | `1`; clicking the next page changes it to `2` |
| `displayLimited` | `False` |
| `sortAlphabetically` | `False` |
| `filterFromToday` | `False` |
| `filteredPoliticalLevelCategories` | Absent initially; checking Justitiedepartementet adds `1287` and resets `page` to `1` |

The root reference comes from `[data-filterbytype="CasePage"][data-rootpage]`
on the requested listing page; it is not a permanent constant in the fetcher.
The response is an object with `TotalCount` (an integer) and `Message` (an HTML
fragment). The UI defaults to 20 results per page. An explicit `pageSize=1000`
was also verified: page 1 returned 1,000 entries, and page 10 returned the
remaining 706 of the then-current 9,706 results. None of those counts are constants.

Each `.sortcompact.sortextended` is one entry:

- `p.sortextended__excerpt strong`: title, with `<br>` separating title lines.
- The next `p.sortextended__excerpt`: labelled agenda number, journal identifiers
  and responsible senior official, separated by `<text>·</text>` elements.
- `.block--timeLinks a`: source weekly page URL and title.
- The text after that link: presenting minister, then department, separated by a comma.

Weekly pages contain the full agenda in `.col-1`: an `h2` meeting-date heading,
then `.c-faq__accordion` blocks with an `h3` department and `section.case` groups.
Each group has an `h4` minister and `article.sortextended` entries headed by `h5`.
The separate `#resultsParent` listing repeats the agenda and must be excluded
from Markdown extraction. Filter checkbox `data-cid` / `title` attributes expose
existing minister and department category codes.

## Public JSON

`api/regeringsarenden.json` is a JSON list. Each run replaces the entries for the
two newest weekly publications and retains the stored entries for older weeks.
For example:

```json
{
    "source": "/regeringsarenden/regeringsarenden-vecka-42-2026/",
    "year": 2026,
    "week": 42,
    "meeting_date": "2026-10-15",
    "department": "Justitiedepartementet",
    "department_code": "1287",
    "minister": "Gunnar Strömmer",
    "minister_code": "2615",
    "agenda_number": "I:10",
    "title": "Regeringens proposition\nEn ny produktansvarslag",
    "journal_ids": ["Ju2025/02091", "Ju2026/01836", "Ju2026/"],
    "responsible_official": "Jonas Pontén"
}
```

`source` is the relative weekly URL supplied by the API. `year` and `week` come
from that page's title in the result, not from the record's publication date.
`meeting_date` comes from the actual Swedish meeting heading on the weekly page;
we never assume that every meeting is on Thursday. A heading without a year is
resolved against the named ISO week, including dates crossing a calendar-year
boundary. Multiple meeting headings are matched to their individual entries;
an ambiguous or unverifiable date is `null`.

Department and minister names preserve the source wording. Optional
`department_code` / `minister_code` fields reference `api/codes.json` when the name
has exactly one known category code. Filter widgets supply additional labels for
the shared code index. Missing minister names, agenda numbers and responsible
officials are `null`; absent journal identifiers produce `[]`.
When the API omits a former minister, an unambiguous matching entry in the weekly
agenda supplies the published minister name. A current minister is never guessed
from the department. Available weekly bodies must agree with the API entry fields
before their metadata or Markdown is published.

Explicit `<br>` title breaks become `\n`. Comma/semicolon-separated journal
identifiers remain separate strings. Incomplete identifiers such as `Ju2026/`
are preserved. Identifiers embedded only in a title are not guessed into the
separate identifier field.

Agenda numbers repeat across departments and occasionally even within a department
on a single weekly page. Journal identifiers may be missing, incomplete or shared.
Neither is a globally unique record ID. Distinct entries with the same agenda
number are retained. The export replaces each refreshed week's complete set of
entries, rather than appending rows from each run. Entries removed from those
weeks disappear from the export. Sorting by year/week (newest first), source,
department, minister and agenda number, with record content breaking ties, is
deterministic. The duplicated on-page filtered listing is never exported again.

## Coverage and failures

Coverage is **modern CasePage entries**, advertised by regeringen.se as the
material from week 38 of 2024 onward. Older PDF publications linked from the
[weekly publication listing](https://www.regeringen.se/arendeforteckningar/)
are not fetched or claimed as part of this export. The inspected snapshot's earliest
entries were week 39 of 2024; absence of another week does not prove that no
meeting occurred.

On 2026-10-17, all 9,706 results were parsed across 104 weekly source URLs.
9,633 had verifiable meeting dates. The remaining 73 pointed to
[`regeringsarenden-vecka-41--2024`](https://www.regeringen.se/regeringsarenden/regeringsarenden-vecka-41--2024/),
which redirected to the homepage. Those API records are retained with a null date,
including their original source URL. Missing historical names/identifiers remain
unknown; current ministers or completed identifiers are not substituted.

The publication listing at `/arendeforteckningar/` supplies the weekly links.
Only modern `/regeringsarenden/` links are selected, ordered by year and week;
the two newest distinct weekly publications are refreshed even across a year
boundary or a gap between publications. Each weekly page supplies its own
CasePage root, so API requests cover only those two weeks, in batches of up to
1,000 entries. The full historical CasePage API listing is not fetched.

Every result page within a selected week must have the expected count and the
same `TotalCount`. Repeated rows or overlapping pages, malformed fragments,
network/JSON failures and a changed first page at the end of a multi-page
traversal reject the snapshot. The fetcher keeps the last complete
`api/regeringsarenden.json` and does not publish a partial list.
Failed weekly requests or a missing weekly CasePage root also reject the
refresh. A recognizable CasePage root with no verifiable meeting heading supplies
no date. Previously stored historical records with unknown dates stay unknown.
There are no permanent checkpoints or extra public report files.

## Running and testing

`uv run fetch.py` refreshes agenda entries alongside the other exports. It reads
the existing `api/regeringsarenden.json` to retain older records, including dates
and recovered minister names. Older weekly pages and their Markdown are not
refetched or rewritten by the agenda refresh. Markdown is repaired only for the
two selected weeks, and unchanged Markdown is not rewritten. On an agenda API
failure, other exports may still be refreshed.

On an empty data directory, only the two latest weekly publications are imported.
Historical entries already in the data directory remain available and accumulate
as the refresh window advances. Corrections or removals outside the two-publication
window are not discovered by this incremental refresh.

To refresh those two weeks, the shared category index and weekly Markdown:

```sh
uv run python -m scripts.fetch_agendas --data-dir data
```

The standalone command exits unsuccessfully if the API snapshot cannot be built,
leaving the previous agenda JSON intact. Publication uses the existing staged
JSON export mechanism.

Offline regression coverage is in `tests/test_agendas.py`. The existing smoke
selection, `uv run python -m pytest tests -m smoke -q`, includes the fixtures and a
bounded live test: one fixed weekly page and its complete API response. It checks
the Markdown hierarchy, source meeting date, incomplete identifiers and agreement
between the weekly body and API records. Offline tests cover pagination, the
two-publication limit, and preservation of historical records.
