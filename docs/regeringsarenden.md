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

`api/regeringsarenden.json` is a JSON list, rebuilt from the complete modern listing.
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
number are retained. The export replaces the whole list on success, rather than
appending rows from each run. Sorting by year/week (newest first), source,
department, minister and agenda number, with record content breaking ties, is
deterministic. The duplicated on-page filtered listing is never exported again.

## Coverage and failures

Coverage is **the modern CasePage listing**, advertised by regeringen.se as the
material from week 38 of 2024 onward. The separate
[older archive](https://www.regeringen.se/arendeforteckningar/) is not traversed
and is not claimed as part of this export. The inspected snapshot's earliest
entries were week 39 of 2024; absence of another week does not prove that no
meeting occurred.

On 2026-10-17, all 9,706 results were parsed across 104 weekly source URLs.
9,633 had verifiable meeting dates. The remaining 73 pointed to
[`regeringsarenden-vecka-41--2024`](https://www.regeringen.se/regeringsarenden/regeringsarenden-vecka-41--2024/),
which redirected to the homepage. Those API records are retained with a null date,
including their original source URL. Missing historical names/identifiers remain
unknown; current ministers or completed identifiers are not substituted.

Every result page must have the expected count and the same `TotalCount`.
Repeated rows or overlapping pages, malformed fragments, network/JSON failures
and a changed first page at the end of traversal reject the snapshot. The fetcher
keeps the last complete `api/regeringsarenden.json` and does not publish a partial
list. Failed weekly requests also reject the refresh. Weekly sources that load
successfully but no longer contain the agenda, such as the historical homepage
redirect above, supply no date and their source count is logged. There
are no permanent checkpoints or extra public report files.

## Running and testing

`uv run fetch.py` refreshes agenda entries alongside the other exports. It also
repairs Markdown for available weekly agendas, including historical pages that
the normal incremental page fetch would otherwise skip. Unchanged Markdown is
not rewritten. On an agenda API failure, other exports may still be refreshed.

To fetch only agenda entries, the shared category index and weekly Markdown:

```sh
uv run python -m scripts.fetch_agendas --data-dir data
```

The standalone command exits unsuccessfully if the API snapshot cannot be built,
leaving the previous agenda JSON intact. Publication uses the existing staged
JSON export mechanism.

Offline regression coverage is in `tests/test_agendas.py`. The existing smoke
selection, `uv run python -m pytest tests -m smoke -q`, includes the fixtures and a
bounded live test: one fixed weekly page and two small API pages. It checks the
Markdown hierarchy, source meeting date, incomplete identifiers and pagination
contract without traversing the full history before every scheduled fetch.
