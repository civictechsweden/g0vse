# Legislative chains

The fetcher writes `api/chains.json` separately from page objects. A page has
`"chains": ["0123456789abcdef"]` only when it belongs to an exported chain.
A document can belong to several chains. Stage and actor describe membership in
a process, not necessarily the document's author or legal status.

## Collection format

```json
{
    "chains": {
        "0123456789abcdef": {
            "phases": [{
                "name": "Lagstiftning i Sverige",
                "ongoing": true,
                "actors": [{
                    "name": "Regeringen",
                    "stages": [{
                        "type": "1327",
                        "documents": [{"url": "/rattsliga-dokument/kommittedirektiv/example/"}]
                    }, {
                        "type": "riksdagsbeslut",
                        "documents": [{
                            "url": "https://www.riksdagen.se/sv/dokument-och-lagar/dokument/betankande/example/",
                            "title": "Example committee report",
                            "date": "2026-06-08"
                        }]
                    }]
                }]
            }]
        }
    }
}
```

Record assembly constructs this structure directly; there is no separate
formatting pass. It implements the agreed `chains.draft.json` structure, followed
by the explicit name-normalization rules below. The draft is not a runtime input.
The only top-level property is `chains`; schema versions and historical aliases
are not part of this public file.

Phase, actor and stage order follows the source, with additional observations
appended in sorted source-view URL order. Stages are an ordered list. A type may
appear more than once. Empty stages, actors and phases are omitted. Known labels
become `type`; unresolved labels retain `name`. Unheaded stages have neither key.
An unheaded block continues the preceding stage within its actor when one exists.

Numeric stage keys refer to `codes.json`. Symbolic keys such as `sfs`,
`riksdagsbeslut`, `eu-direktiv` and `eu-forordning`, plus explicitly registered
additional EU types, are declared in `services/chain_normalization.py`.

Indexed documents use their exact item URL and the item's canonical title and
identifier. Their redundant chain titles are omitted. If an indexed item has no
title, its source title remains as a fallback. Dates matching the item's
publication date on the calendar day are omitted. A differing date is retained
and reported for review. Unindexed and external documents retain source titles
and any available dates, with their original precision. Null dates are omitted.
Exact duplicate public document variants collapse within a stage.

There is no repeated `id`, `external_ids`, `sources` or `current_page` in public
records. Original titles, dates, markers, selectors and provenance remain in the
checkpoint and diagnostics. Local `.aspx` and `/t/<id>/sv` redirects are resolved
and cached before reconciliation; failures preserve the previous observation.
Other local URLs are relative with trailing slashes, except exact indexed item
URLs and file URLs. External links remain absolute. Fragments are removed.

## Meaning of `ongoing`

`ongoing` records the website's ongoing marker on a **phase**:

- `true`: the modern layout supplies the marker for that phase.
- `false`: that layout supplies the phase without the marker. This does not
  establish that the process is completed, abandoned or not yet started.
- Absent: the layout supplies no status, or observations disagree. Combining a
  known status with an unknown status also yields an unknown status.

The older layout supplies no marker and is still used on pages published in
2026. Neither the layout nor an unknown status establishes the age or completion
of a process. An absent property means the same as the legacy export's `null`, never
`false`. Do not infer status from the latest document, an SFS link or an empty
stage. Source observations and the quality report retain the evidence.

## Deterministic identity and public keys

Internal identities retain the existing `chain-` plus full SHA-256 of JSON
serialized with Python's `json.dumps(value, ensure_ascii=False, sort_keys=True)`
(default separators):

1. Explicit CELEX selector: `["celex", sorted_identifiers]`. A bundle is distinct
   from each constituent identifier. Unselected EU views use proposal links in
   the first EU proposal phase. An explicitly empty selector falls back to
   membership identity. Other CELEX links do not determine identity.
2. Otherwise: `["members", [first_url, second_url]]`, with distinct normalized
   member URLs ordered by their earliest source date, then URL; undated last.
   Both anchors must match to combine observations.
3. With fewer than two members: `["source", normalized_view_url]`.

One shared member is never sufficient to merge. Even two matching anchors are an
inference, not an authoritative government process identifier. Titles, stage
names and normalization results do not participate in identity.

Stored source-to-internal-ID assignments preserve identity across title edits,
later steps, singleton growth and discovery of earlier documents. A merge keeps
the smallest eligible previous internal ID; the others become aliases. A split
retains the old ID for the successor with the smallest initial candidate ID.
Internal alias targets resolve directly to live records. A split can retain its
old ID among its own successors. These aliases are checkpoint history only.

For example, merging internal identities `A < B` leaves `A` and `aliases[B] = [A]`.
Splitting that process can leave `A` and `D`, with `aliases[A] = [A, D]`; the old
merge alias becomes `aliases[B] = [A, D]` as well. These letters stand in for real
identities. These full internal IDs and aliases are not exported in `chains.json`.

The checkpoint's `public_ids` registry assigns each internal identity a public
key, normally the first 16 hash characters without `chain-`. Published keys are
reserved even after retirement. A colliding new identity receives a longer
prefix; existing keys never change. Clean builds assign keys in sorted internal
identity order. Existing publications also require the saved registry for exact
reproduction. Internal identity order determines the survivor of a merge, not
necessarily the lexical order of shortened public keys.

The lean format replaces the legacy export's full public IDs. Chain keys, item
references and diagnostic IDs are rebuilt from the same mapping. Internal
assignments and aliases remain full-length in the checkpoint. Consumers should
refresh chains and item references together; the public file provides neither
schema-version negotiation nor redirects for cached IDs after merges or splits.

Keep `data/.chain-state/state.json`: observations, parser versions, hashes,
redirects, assignments, aliases, public IDs and backfill checkpoints are part of
the reproducible build input. A stateless rebuild cannot recover ID history.
The state remains version 1 with an additive `public_ids` field; existing version
1 checkpoints load without another historical download.

A successful refresh replaces its source view. A fetch/parse failure preserves
its previous observation. A recognized page without a chain clears only that
view. Missing members in one view do not remove members in others. Removed
selector choices remain until explicitly revisited. Source title/date variants
remain available even when the public document uses canonical item metadata.

## Normalization and evidence

The stages are:

1. **Parse sources:** retain original headings, dates, markers and selectors.
2. **Reconcile and assemble records:** retain identity history, allocate public
   keys, merge source evidence and construct the lean structure.
3. **Normalize odd stage names:** classify links and independently check indexed
   item types. Uniform types replace a named fallback with `type`. Mixed types
   split into consecutive runs, preserving exact document order. Unknown,
   partial or contradictory evidence retains the original heading. There is no
   majority vote. Standard typed stages and unheaded EU groups keep their meaning.
4. **Report:** retain the original value, result or suggestion, rule, chain,
   document links, phase/actor context, department and one representative source
   view. Reporting never rewrites source observations.

Mappings can intentionally adopt a broader document type: `Remissvar` becomes
`Remiss`, for example. These are vocabulary choices, not proven website errors.
Riksdagen also hosts propositions and government communications. Its committee
reports fit the site's Riksdagsbeslut group but do not prove a decision was made.
EUR-Lex requires CELEX sector/type or ELI evidence, not domain-only guessing.
Item/URL contradictions remain explicit. Dates and actor/group headings are
reported for review, not inferred from document type or silently changed.

`api/chains-normalization.json` is a deterministic snapshot with counts,
`findings` and a `recheck` list. Findings have stable IDs independent of the chosen
representative page. `normalized` records applied stage mappings/splits;
`review` records unresolved stages, actor/groups, date differences and type
contradictions. Departments come from the representative source's indexed
senders and `codes.json`; missing attribution is explicit. Date suggestions use
the item's publication date while retaining the original public chain date.

`api/chains-report.json` retains fetch/parse failures, shared-member ambiguities,
source conflicts and the combined recheck queue. Ambiguities may be legitimate
participation in several processes. A conflict or review is not proof of an
upstream error. Both reports refer to the new public chain keys.

The download workflow appends a bounded summary to `GITHUB_STEP_SUMMARY`: counts,
new/no-longer-observed findings and at most 20 representative examples, capped at
40 KB. The `chain-normalization` Actions artifact contains complete JSON and a
Markdown table with one row per finding/chain, not one row per source page.
Original untruncated values remain in JSON. Artifacts are retained for 90 days;
the current JSON snapshot is also published with the API and committed on the
data branch. Corrections become visible after the affected views are refreshed;
"no longer observed" does not mean every page was freshly checked.

## Fetching and rebuilding

Normal `uv run fetch.py` observes fetched pages and follows same-page selector
choices, including empty and bundled selectors. It does not redownload the
historical corpus on every scheduled run.

To rebuild the new schema and normalization from the existing checkpoint, without
a browser or network:

```bash
uv run backfill_chains.py --export-only
```

This preserves previous failures and queued checks because it has not revisited
those pages. To continue a historical backfill:

```bash
uv run backfill_chains.py --limit 1000
```

Repeat to resume; completed pages are skipped and failed pages remain eligible.
Omit `--limit` for the full corpus. `--retry` refreshes completed pages. `--recheck`
revisits exact queued source views, including selectors no longer linked on the
page and all views underlying normalization findings. Bounded rechecks retain
unattempted failures and checks. A corrected representative page alone does not
clear still-unrefreshed observations from other pages.

For example, with `["/page/?id=52025PC0989", "/other/"]` queued, `--recheck --limit 1`
fetches the selected view directly. Success clears that check unless current
findings still require it; `/other/` remains pending for the next run.

The terminal prints progress and compact counts; complete findings stay in the
report files. Checkpoints are saved every 100 attempts and on interruption. Do
not run the fetcher and backfill concurrently against the same directory. A
bounded run publishes its successfully observed subset.

All JSON files are serialized to a staging directory before replacements begin.
Items, type collections, chains and both reports use the same export. Local
renames are individually atomic, not a multi-file filesystem transaction. A
successful command followed by one Git commit/Pages artifact remains the public
publication boundary. Never commit a failed/interrupted export. The Pages
workflow excludes `.chain-state`; keep that directory on the data branch.

## Implementation guide

| Module | Responsibility |
| --- | --- |
| `services/chain_parser.py` | Parse a selected source view without normalizing its evidence. |
| `services/chain_reconciliation.py` | Reconcile full identities, aliases and stable public keys. |
| `services/chain_records.py` | Merge evidence, assemble lean records, build quality diagnostics and item references. |
| `services/chain_normalization.py` | Explicit type rules and conservative stage-name normalization. |
| `services/chain_diagnostics.py` | Collect original values, source/department evidence and stable finding IDs. |
| `services/chain_reporting.py` | Compact console/Actions summary and complete downloadable reports. |
| `services/chains.py` | Orchestrate an export without changing stored identity history. |

JSON shapes are declared in `services/chain_types.py`. `ChainStore.build_export`
returns the collection, both reports, public item references, internal assignments
and aliases, and the proposed public ID registry. It changes neither items nor
stored state. Callers apply item references, publish all JSON together, then call
`update_identity_history` and `save`. The `normalize=False` build option exists
for contract comparisons against the original draft structure.

`uv run audit_chain_types.py` measures URL rules against original source
headings, including after a lean export. It reads checkpoint evidence for
lean exports and accepts an optional `--draft` to restrict the labels under review.
The earlier [URL analysis](chains-url-analysis.md) describes the backfill audit.
