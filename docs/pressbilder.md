# Press portraits

`api/pressbilder.json` lists press-portrait entries separately from the publication
pages in `api/items.json`. Each portrait page also has a Markdown export at its
source path, for example `/pressbilder/ulf-kristersson2/` becomes
`pressbilder/ulf-kristersson2.md`. Image binaries remain on regeringen.se; the
export contains links and metadata.

## Source and schema

The root reference is read from the directory at `/pressbilder/`, using
`[data-filterbytype="PressImagePage"][data-rootpage]`. The observed root was `108`;
it is not hard-coded. The API request uses `filterType=Structure`,
`filterByType=PressImagePage`, `lang=sv`, `displayLimited=False`,
`sortAlphabetically=True`, `filterFromToday=False`, `page=1`, and `pageSize=1000`.

This listing returns all matching portrait cards on its first page without
pagination controls. The observed 2026-10-18 snapshot had 91 entries covering 61
distinct names. The implementation requires the number of parsed cards to equal
`TotalCount` and repeats the request to detect changes. It rejects a partial list
rather than assuming the calendar paginator works for portraits too.

| Field | Meaning |
| --- | --- |
| `url` | Relative portrait-page URL; identity within this export |
| `name` | Person's displayed name |
| `department` | Source department group heading |
| `role` | Optional source position text, without vocabulary normalisation |
| `thumbnail` | Absolute original-site thumbnail URL |
| `alt` | Optional image alternative text |
| `image` | Optional absolute high-resolution image URL from the detail page |
| `caption` | Optional image caption |
| `credit` | Optional photographer/organisation credit, preserving source wording |
| `rights` | Optional usage terms from the detail page |
| `published`, `updated` | Optional source publication dates |
| `categories` | Optional detail-page category codes referencing `api/codes.json` |

There can be multiple portraits for the same person. Records are not merged by
name and this is not an authoritative historical list of officeholders. Category
codes may refer to the associated minister and department; a staff portrait does
not necessarily have its own person code. Department, name and URL determine the
stable output order. Missing optional fields are omitted, and `updated` is omitted
when equal to `published`.

Markdown retains the portrait, role, caption, photographer credit, original-image
link and source usage text where available. Thumbnail and original-image URLs
point to regeringen.se; the project does not copy the image files. Consumers need
to preserve the image credits and the accompanying usage terms.

## Refreshing and failures

`uv run fetch.py` refreshes the complete small collection, including detail pages,
each run. This catches caption, credit and usage-text edits even when the listing
has not changed. Unchanged Markdown is not rewritten. The public JSON and Markdown
on the data branch provide the previous state; there is no checkpoint.

A missing/ambiguous root, malformed response, empty/partial list, repeated URL or
changed listing rejects the snapshot and keeps the previous JSON and codes.
Other datasets can still refresh. Individual detail-page failures retain the
previous record and Markdown or produce a new listing-only record and Markdown.
Missing detail fields remain unknown and all detail pages are retried next run.
Warnings include a count and up to five affected URLs. Successful runs replace
the JSON list; old unlisted Markdown is not deleted.

To fetch only portraits, shared codes and portrait Markdown:

```sh
uv run python -m scripts.fetch_press_images --data-dir data
```

The standalone command exits unsuccessfully when the complete listing cannot be
validated. Offline fixtures and a bounded live listing/detail check use the existing
`pytest -m smoke` selection.
