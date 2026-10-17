# Legislative chains

The fetcher writes `api/chains.json` and adds `chains` references to participating
items. The existing collection on the data branch is the baseline for scheduled
runs. There is no separate checkpoint or stored observation history.

## Public format

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

Stages are an ordered list; the same type can appear more than once. Empty
stages, actors and phases are omitted. Known labels become `type`; unresolved
labels retain `name`. Unheaded stages have neither key. Numeric types refer to
`codes.json`; symbolic types cover SFS, Riksdagsbeslut and EU documents. Rules
are declared in `services/chains/normalization.py`.

Indexed documents use the exact item URL and canonical item title/identifier.
Their chain titles are omitted, with a source-title fallback when the item has
no title. Dates matching the item's publication day are omitted. Differing dates
are retained and reported. External and unindexed documents retain available
source titles and dates. Null dates are omitted. Exact duplicate public variants
collapse within a stage.

The collection has no `version` or `aliases`; records have no repeated `id`,
`external_ids`, `sources` or `current_page`. Original source values exist only in
memory during parsing and in optional local diagnostics. Record assembly creates
the lean structure directly, without a separate formatting pass.

## Meaning of `ongoing`

`ongoing` records the website's marker on a phase:

- `true`: the modern layout supplies an ongoing marker.
- `false`: that layout supplies the phase without the marker. This does not
  establish that the process is completed, abandoned or not yet started.
- Absent: the layout supplies no status or current observations disagree.

The older layout supplies no marker and is still used on pages published in
2026. An absent status never means `false`. Do not infer completion from dates,
an SFS link or the age of the layout. Actors and stages describe process
membership, not necessarily document authorship or legal status.

## Identity and incremental updates

Fresh views are grouped deterministically using SHA-256 of sorted-key JSON:

1. `["celex", sorted_identifiers]` for an explicit CELEX selector or proposal
   identifiers in the first EU proposal phase. A bundle is distinct from each
   constituent; an explicitly empty selector uses membership identity instead.
2. `["members", [first_url, second_url]]`, using distinct member URLs ordered
   by earliest source date, then URL, with undated members last.
3. `["source", normalized_view_url]` for fewer than two members.

New public keys use the first 16 hash characters; collisions extend the prefix.
Matching refreshes reuse an existing published key. An exact hash can identify an
existing chain; otherwise a refreshed source must already be a member, share both
old anchors and identify exactly one candidate. EU proposal bundles must agree.
A source that was its chain's sole member can grow while retaining its key.
One shared member never combines unrelated processes. Ambiguous matches remain
separate, rather than forcing a merge.

Fresh records update matching phases, actors and ordered stage occurrences.
New metadata replaces previous variants of the same URL in that stage; unseen
memberships, stages and chains remain. This preserves historical coverage when
the daily fetch touches only a few pages or a request fails. It is deliberately
additive: a missing document or empty view does not prove that an entire published
chain should be deleted. A full fresh backfill can replace obsolete records.

There is no permanent ID registry, alias history or authoritative government
process ID. Ambiguous identity changes can create another record. Consumers
should refresh chains and item references together. The current collection and
item metadata are the only persistent inputs; the output is reproducible from
these inputs and the same fetched views.

## Normalization and reporting

The implementation separates these responsibilities:

1. Parse current pages, retaining raw headings, dates and source links in memory.
2. Group views and construct lean records using document-type keys.
3. Normalize nonstandard stage names using explicit URL rules and indexed item
   types. Uniform evidence supplies a type. Mixed types split into consecutive
   runs, preserving document order. Unknown or contradictory evidence keeps the
   original heading. There is no majority vote.
4. Merge the results into the published collection and report this run's findings.

Recognized typed stages and unheaded EU groups retain their meaning. Types can
be intentionally broader than a source label: for example, `Remissvar` becomes
`Remiss`. Committee reports fit the site's Riksdagsbeslut group but do not prove
a decision occurred. EUR-Lex classification requires CELEX or ELI evidence.
Dates and actor headings are flagged for review, without automatic corrections.

GitHub Actions keeps a Markdown job summary with counts and up to 20 representative
examples, capped at 40 KB. It uploads no diagnostic artifact and publishes no
report JSON. Only `chains.json` is added as a public chain data file; existing
items and type collections continue to receive matching chain references.

Complete diagnostics can be generated locally while fetching:

```bash
uv run python -m scripts.backfill_chains --report-dir /tmp/chain-reports
```

The optional directory contains `chains-report.json`, `chains-normalization.json`
and `chains-normalization.md`. Findings include the original/suggested value,
rule, department and one representative fetched source view. They do not list
every page that exhibits the same chain issue. Original untruncated values remain
in JSON; the Markdown table abbreviates long cells. Missing attribution is
explicit. Diagnostics describe fetched views from this run, not unvisited pages
in the baseline. A review finding is not proof of an upstream error.

## Local backfills

Build full historical coverage locally, or update an existing collection:

```bash
uv run python -m scripts.backfill_chains
```

Use `--fresh` to replace the collection with this run's observations, including
when replacing the earlier experimental schema. A fresh bounded run publishes
only its selected subset. To process an explicit range of the current item list:

```bash
uv run python -m scripts.backfill_chains --offset 1000 --limit 1000
```

Ranges refer to positions in `items.json`; keep that index unchanged between
batches. No progress file is written. Each selected page is fetched, including
its selector views. Retry an exact set of affected views using an optional local
quality report:

```bash
uv run python -m scripts.backfill_chains --recheck /tmp/chain-reports/chains-report.json --report-dir /tmp/chain-reports
```

A bounded recheck retains unattempted failures/views in its optional output
report. Without a local report there is no persisted retry queue. The terminal
prints progress and compact counts. Normal `fetch.py` observes only pages it
fetches and combines their chains with the committed baseline.

Items, type collections and chains are serialized before replacement. Individual
renames are atomic, rather than a multi-file transaction; a successful export
followed by a Git commit/Pages deployment is the publication boundary. Do not run
fetch and backfill concurrently against the same directory.

## Implementation guide

All chain services live under `services/chains/`:

| Module | Responsibility |
| --- | --- |
| `parser.py` | Parse a selected source view and discover selector choices. |
| `reconciliation.py` | Group current views and match published identities. |
| `records.py` | Assemble lean records and quality diagnostics. |
| `normalization.py` | Explicit document-type rules and stage-name normalization. |
| `merge.py` | Preserve untouched public data while applying fresh records. |
| `diagnostics.py` | Collect findings and original source evidence for this run. |
| `reporting.py` | Console/Actions summary and opt-in local reports. |
| `export.py` | Stage JSON before publishing. |
| `store.py` | Orchestrate current observations and the public baseline in memory. |
| `types.py` | Shared JSON and internal data shapes. |

Callers import `ChainStore` from `services.chains`. `build_export` mutates neither
items nor the baseline; callers apply item references and publish the result.
`normalize=False` allows comparisons against the agreed draft structure.

`uv run python -m scripts.audit_chain_types` audits URL/type consistency in the
published collection. It cannot recover original headings already normalized;
use a fresh backfill for original source evidence.
