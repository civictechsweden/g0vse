# Legislative chains

The fetcher writes `api/chains.json` separately from page objects. A page has
`"chains": ["chain-…"]` only when it belongs to an exported chain. A document can
belong to several chains. Stage and actor are properties of chain membership.

## Collection format (version 1)

```json
{
    "version": 1,
    "chains": {
        "chain-<sha256>": {
            "id": "chain-<sha256>",
            "external_ids": {"celex": ["52025PC0989"]},
            "phases": [{
                "name": "Förhandling och beslut inom EU",
                "ongoing": true,
                "actors": [{
                    "name": "Regeringen",
                    "stages": [{
                        "name": null,
                        "documents": [{
                            "url": "/kommenterade-dagordningar/example/",
                            "title": "Example",
                            "date": "2026-06-08",
                            "current_page": true,
                            "sources": ["/kommenterade-dagordningar/example/?id=52025PC0989"]
                        }]
                    }]
                }]
            }],
            "sources": ["/kommenterade-dagordningar/example/?id=52025PC0989"]
        }
    },
    "aliases": {}
}
```

Phase, actor and stage order follows the source, with additional observations
appended in sorted source-URL order. Empty stages remain present. Missing stage
names/dates are null. Blocks without a heading continue the preceding stage
within the same actor; actors without stage headings retain a null stage name.
Dates retain source precision. `ongoing` is null when the
layout supplies no status or observations disagree. `current_page` means at least
one source explicitly marked that membership as the page being viewed; it is not
a statement about which document is the latest. `sources` identifies those source
views, including the selector query. Observations retain each view's exact marker.

Local membership URLs use the exact item URL when an item exists, so consumers can
join on `url`. Other regeringen.se URLs use relative paths with a trailing slash;
external links remain absolute. Fragments are removed. Local `.aspx` and numeric
`/t/<id>/sv` links are resolved and cached. Redirect failures preserve the previous
observation; numeric page IDs are never used as chain IDs.

## Deterministic identity and reconciliation

The initial ID is `chain-` plus the full SHA-256 of JSON serialized with Python's
`json.dumps(value, ensure_ascii=False, sort_keys=True)` (default separators):

1. For an explicit CELEX selector, the value is `["celex", sorted_identifiers]`.
   A bundle of CELEX identifiers is distinct from each constituent identifier.
   Unselected EU views use the CELEX proposal links in the first EU proposal
   phase. An explicitly empty selector falls back to membership identity.
   Other CELEX links are retained as external identifiers, not identity anchors.
2. Otherwise, the value is `["members", [first_url, second_url]]`, using distinct
   normalized member URLs ordered by their earliest source date and then URL.
   Undated documents sort last. Both anchors must match to combine observations.
3. With fewer than two members, the value is `["source", normalized_view_url]`.

This deliberately leaves partial views with different anchors separate. One shared
member is a possible match, never enough to merge. Even two matching anchors are
an inference, not an authoritative government process identifier. Titles and stage
names do not participate in identity. Identical observations produce identical
IDs and output, irrespective of discovery order on a clean build.

The stored source-to-ID assignments preserve published IDs across refreshes,
including title edits, later stages, singleton growth and discovery of an earlier
document. A merge retains the lexicographically smallest eligible previous ID;
other published IDs become aliases. On a split, the successor with the smallest
initial candidate ID retains the old ID. `aliases[old_id]` lists all live successors
(including the retained ID for a split). Alias targets resolve directly to records.
Clients should consult aliases even if the old ID still exists as a record.

For example, suppose `/view-a/` lists documents `/a/`, `/b/` and has published ID
`A`, while `/view-b/` lists `/b/`, `/c/` and has ID `B` (`A < B`). If `/view-b/`
changes to list `/a/`, `/b/`, the matching anchor pairs merge into `A` and
`aliases[B]` becomes `[A]`.

For a split, suppose two views previously shared `A` but now have different anchor
pairs. The pair with the smaller initial hash keeps `A`; the other gets its own
ID, say `D`. Both records are live, and `aliases[A]` is `[A, D]`. These letters
stand in for the full chain IDs. See the separate merge and split scenarios in
`tests/test_chains.py`.

Keep `data/.chain-state/state.json` when rebuilding an existing publication: it is
part of the reproducible build input and contains observations, parser versions,
content hashes, redirects, assignments, aliases and backfill checkpoints. A clean
build from only today's HTML cannot recover the history of previous IDs. Losing
this state loses that history; do not publish a stateless rebuild over an existing
API without preserving its previous IDs/aliases.

A successful source refresh replaces that view's observation. A fetch failure or
unrecognized layout leaves its last successful observation intact. A recognized
page without a chain clears only that source's observation. Missing memberships
in one view do not delete memberships still present in another. Removed selector
choices are retained until explicitly re-observed; absence alone is insufficient
proof that a chain has ceased to exist.

Different title/date variants for the same membership are preserved with source
provenance. `api/chains-report.json` counts parser/fetch failures, ambiguous matches
(shared URLs across separate chains) and conflicting observations. Its `recheck`
list provides source views to revisit. Some ambiguities represent legitimate
participation in multiple chains. Reports describe the current build; the stored
observations provide the evidence for inspection.

## Fetching and backfilling

Normal `uv run fetch.py` observes chains on each page it fetches and follows all
same-page chain selector links, including empty and bundled selectors. It does not
force a historical corpus download on every scheduled run.

With a local checkout of the `data` branch in `data/`, run:

```bash
uv run backfill_chains.py --limit 1000
```

Repeat to resume; successful pages are skipped. Failed pages remain eligible.
Omit `--limit` for the full corpus. Use `--retry` to refresh already completed pages.
Use `--recheck` to revisit the exact source views queued in the last build report,
including selectors no longer linked from the page. With `--limit`, unattempted
sources and their previous failures remain queued for the next recheck. Successful
rechecks clear previous failures; new failures keep the last successful observation.
Checkpoints are saved every 100 attempts and on interruption. Do not run backfill
and the regular fetcher concurrently against the same data directory. A bounded
run publishes the successfully observed subset; coverage grows with later runs.

For example, with failed views `["/page/?id=52025PC0989", "/other/"]` queued,
`--recheck --limit 1` fetches the selected `/page/` view directly. If it succeeds,
the new report queues only `/other/`, retaining that view's previous error. The
next recheck visits `/other/`; it does not restart at the successfully checked view.

All JSON is indented and serialized to a staging directory before replacing any
public files. Item references, type collections, chains and report are built from
the same observation set. Local renames are individually atomic, not a filesystem
transaction across files. The existing single Git commit and GitHub Pages artifact
are the atomic public publication boundary: never publish midway through a run.
An interrupted/failed command must not be committed. The Pages workflow excludes
internal `.chain-state` files; keep them on the data branch for the next build.

## Implementation guide

The code follows three steps: parse source observations, reconcile identities,
then build public records and a quality report. The JSON data shapes are declared
in `services/chain_types.py`; they are ordinary dictionaries at runtime.

| Module | Responsibility |
| --- | --- |
| `services/chain_parser.py` | Parse one source view into phases, actors, stages and documents. |
| `services/chain_reconciliation.py` | Choose IDs, retain published IDs and resolve aliases to live successors. |
| `services/chain_records.py` | Merge documents with provenance, build the report and apply item references. |
| `services/chains.py` | Store observations and assemble the export without changing identity history. |

An `item_url` identifies a page, for example `/page/`. A `source_view_url`
identifies the particular chain view, for example `/page/?id=52025PC0989`.
The stored JSON field `source` contains that view URL. Documents marked as the
current page always use `item_url`, so references can join back to page objects.

`ChainStore.build_export(items, pending_source_views)` returns a `ChainExport`
containing the collection, report, item references and proposed assignments. It
does not change the items or stored observations, assignments or aliases.
Callers make the changes explicit:

1. Build the export from observations and previous identity history.
2. Call `apply_item_chain_references(items, export.item_references)` to update page objects.
3. Assemble and publish all JSON files with `publish_json`.
4. Call `store.update_identity_history(export)` and `store.save()` to remember the published IDs.

The parser also keeps source rules local. A domestic block headed “Statens
offentliga utredningar” followed by an unheaded SOU block becomes one stage with
both documents. An EU actor with no stage headings has a stage named null.
Only the explicit “Inga dokument” placeholder marks an empty modern block;
tooltip icons do not provide evidence that a document is absent.
