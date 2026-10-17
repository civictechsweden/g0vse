"""Measure URL type rules against the saved backfill without changing its data."""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit

from services.chains.normalization import (
    TYPE_NAMES,
    infer_document_type,
    infer_stage_type,
    stage_type_from_name,
    type_from_url,
)
from services.chains.records import DRAFT_STAGE_TYPES


class UrlGroup(TypedDict):
    memberships: int
    urls: set[str]
    types: Counter[str]


def local_key(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.hostname and parts.hostname.removeprefix("www.") not in {
        "regeringen.se",
        "g0v.se",
    }:
        return None
    return parts.path.rstrip("/")


def group_key(url: str) -> str:
    parts = urlsplit(url)
    if parts.hostname and local_key(url) is None:
        return parts.hostname.removeprefix("www.")
    segments = parts.path.strip("/").split("/")
    return "/" + "/".join(
        segments[:2] if segments[0] == "rattsliga-dokument" else segments[:1]
    )


def analyse(data_dir: Path, draft_path: Path | None = None) -> dict:
    collection = json.loads((data_dir / "api/chains.json").read_text())
    item_list = json.loads((data_dir / "api/items.json").read_text())
    items = {local_key(i["url"]): i for i in item_list}
    chains = collection["chains"]
    # The published schema omits canonical metadata and raw source provenance.
    # For this URL audit, the document page itself is the example link.
    for chain in chains.values():
        for phase in chain["phases"]:
            for actor in phase["actors"]:
                for stage in actor["stages"]:
                    stage["name"] = stage.get("name") or TYPE_NAMES.get(
                        stage.get("type")
                    )
                    for document in stage["documents"]:
                        item = items.get(local_key(document["url"]), {})
                        document.setdefault("date", item.get("published"))
                        document.setdefault("title", item.get("title"))
                        document.setdefault("sources", [document["url"]])
    if draft_path is not None:
        draft = json.loads(draft_path.read_text())
        exotic_names = {
            s["name"]
            for c in draft["chains"].values()
            for p in c["phases"]
            for a in p["actors"]
            for s in a["stages"]
            if "name" in s
        }
    else:
        exotic_names = {
            s["name"]
            for c in chains.values()
            for p in c["phases"]
            for a in p["actors"]
            for s in a["stages"]
            if s["name"] and stage_type_from_name(s["name"]) not in DRAFT_STAGE_TYPES
        }
    groups: defaultdict[str, UrlGroup] = defaultdict(
        lambda: UrlGroup(memberships=0, urls=set(), types=Counter())
    )
    guesses = {}
    first_membership = {}
    exotic_stages = []
    mixed_stages = []
    heading_disagreements = []
    membership_count = 0

    def representative_source(documents):
        sources = {s for d in documents for s in d["sources"]}
        return max(
            sources,
            key=lambda s: (
                items.get(local_key(s), {}).get("published") or "",
                s,
            ),
        )

    for chain_id, chain in chains.items():
        for phase in chain["phases"]:
            for actor in phase["actors"]:
                for stage in actor["stages"]:
                    documents = list({d["url"]: d for d in stage["documents"]}.values())
                    if not documents:
                        continue
                    context = {
                        "chain": chain_id,
                        "phase": phase["name"],
                        "actor": actor["name"],
                        "name": stage["name"],
                        "source": representative_source(documents),
                    }
                    stage_guesses = []
                    evidence = []
                    for document in documents:
                        url = document["url"]
                        item = items.get(local_key(url), {})
                        if url not in guesses:
                            guesses[url] = infer_document_type(
                                url, item.get("types", [])
                            )
                        guess = guesses[url]
                        stage_guesses.append(guess)
                        evidence.append({"url": url, **asdict(guess)})
                        first_membership.setdefault(
                            url,
                            {**context, "source": representative_source([document])},
                        )
                        membership_count += 1
                        bucket = groups[group_key(url)]
                        bucket["memberships"] += 1
                        bucket["urls"].add(url)
                        bucket["types"][guess.type or guess.reason] += 1
                    stage_guess = infer_stage_type(stage_guesses)
                    case = {**context, **asdict(stage_guess), "documents": evidence}
                    if stage["name"] in exotic_names:
                        exotic_stages.append(case)
                    if stage_guess.reason == "mixed":
                        mixed_stages.append(case)
                    heading_type = stage_type_from_name(stage["name"])
                    if (
                        heading_type
                        and stage_guess.type
                        and heading_type != stage_guess.type
                    ):
                        heading_disagreements.append(
                            {**case, "heading_type": heading_type}
                        )

    url_only_count = sum(type_from_url(url) is not None for url in guesses)
    classified_count = sum(guess.type is not None for guess in guesses.values())
    summary = {
        "chains": len(chains),
        "memberships": membership_count,
        "unique_urls": len(guesses),
        "url_only_classified_urls": url_only_count,
        "metadata_checked_classified_urls": classified_count,
        "document_types": dict(Counter(g.type for g in guesses.values() if g.type)),
        "exotic_stages": len(exotic_stages),
        "exotic_names": len({s["name"] for s in exotic_stages}),
        "exotic_stage_results": dict(Counter(s["reason"] for s in exotic_stages)),
        "mixed_stages": len(mixed_stages),
        "heading_disagreements": len(heading_disagreements),
    }
    return {
        "summary": summary,
        "method": "Read-only analysis of the saved source evidence. Count each distinct URL once within a chain/phase/actor/source stage; repeated title/date variants do not inflate frequencies. Hosts differing only by www are combined. A supplied draft can optionally select exotic labels; otherwise the agreed stage vocabulary is used. Each finding has one representative source view.",
        "groups": [
            {
                "group": key,
                "memberships": bucket["memberships"],
                "unique_urls": len(bucket["urls"]),
                "types": dict(bucket["types"].most_common()),
                "example": min(bucket["urls"]),
            }
            for key, bucket in sorted(
                groups.items(), key=lambda kv: (-kv[1]["memberships"], kv[0])
            )
        ],
        "unclassified_documents": [
            {"url": url, **asdict(guess), **first_membership[url]}
            for url, guess in sorted(guesses.items())
            if guess.type is None
        ],
        "exotic_stages": exotic_stages,
        "mixed_stages": mixed_stages,
        "heading_disagreements": heading_disagreements,
    }


def markdown(report: dict) -> str:
    summary = report["summary"]

    def link(url):
        return "https://www.regeringen.se" + url if url.startswith("/") else url

    def names(types):
        return ", ".join(TYPE_NAMES.get(t, t) for t in types) or "unknown"

    lines = [
        "# Document types inferred from chain links",
        "",
        "Analysis of the published collection, not a new crawl. Original source-label evidence requires a fresh local backfill.",
        "",
        f"{summary['chains']:,} chains; {summary['memberships']:,} stage memberships; {summary['unique_urls']:,} distinct URLs. Repeated title/date variants of the same membership are counted once. Hosts differing only by `www` are combined. Other host spellings remain distinct.",
        "",
        f"URL rules classify **{summary['url_only_classified_urls']:,}/{summary['unique_urls']:,} distinct URLs**. Checking indexed item types leaves **{summary['metadata_checked_classified_urls']:,}** classified URLs; contradictions are reported rather than overwritten.",
        "",
        "## Popular URL groups",
        "",
        "| URL prefix or domain | Memberships | Distinct URLs | Inferred document types |",
        "| --- | ---: | ---: | --- |",
    ]
    for group in report["groups"]:
        types = ", ".join(
            f"{TYPE_NAMES.get(t, t)} ({n:,})" for t, n in group["types"].items()
        )
        lines.append(
            f"| `{group['group']}` | {group['memberships']:,} | {group['unique_urls']:,} | {types} |"
        )
    lines += [
        "",
        "## Which exotic stages can be normalized?",
        "",
        f"The current draft has **{summary['exotic_stages']} exotic stage occurrences**, with **{summary['exotic_names']} distinct labels**. Their results are:",
        "",
    ]
    for reason, count in summary["exotic_stage_results"].items():
        lines.append(f"- `{reason}`: **{count}** stages.")
    lines += [
        "",
        "`uniform` means every member has the same compatible type. These stages can receive the inferred type while retaining their documents, actor, phase and order. `mixed` stages can be split by document type if that is the chosen presentation rule. `partial` and `unknown` stages remain unresolved. A majority vote is never used.",
        "",
        "| Existing heading | Inferred type / candidates | Result | Example source |",
        "| --- | --- | --- | --- |",
    ]
    # One representative per label/result/type combination, rather than all pages.
    examples: dict[tuple[str, str, tuple[str, ...]], dict] = {}
    for case in report["exotic_stages"]:
        key = (case["name"], case["reason"], tuple(case["candidates"]))
        examples.setdefault(key, case)
    for (name, reason, candidates), case in sorted(examples.items()):
        lines.append(
            f"| {name} | {names(candidates)} | {reason} | [source]({link(case['source'])}) |"
        )
    lines += [
        "",
        "## URL outliers and contradictory metadata",
        "",
        "| Document | Reason | Candidate types | Example source |",
        "| --- | --- | --- | --- |",
    ]
    for case in report["unclassified_documents"]:
        lines.append(
            f"| [document]({link(case['url'])}) | {case['reason']} | {names(case['candidates'])} | [source]({link(case['source'])}) |"
        )
    lines += [
        "",
        "## Ambiguities that must stay explicit",
        "",
        "- **Document type versus process stage.** Riksdagen hosts propositions and government communications too. Committee reports can be displayed under Riksdagsbeslut, but are proposals for a decision, not proof that a decision has been made. Known process-stage headings are not automatically replaced because a linked document has another type.",
        "- **More specific source labels.** Remissvar, Delrapport, Tilläggsremittering and Budgetförslag may convey a role or subtype beyond the linked page's general document type. The 150 uniform results are type-normalization candidates, not 150 proven errors. Adopting a coarser vocabulary is an explicit schema choice.",
        "- **Mixed stages.** A heading can contain multiple types. Normalize each document first; split only exotic stages with complete evidence, preserving the order of first appearance. Keep a diagnostic instead of forcing one type.",
        "- **Item metadata versus URL.** The indexed draft referral on market surveillance is labelled Lagrådsremiss but its path is Departementsserien och promemorior. That conflict requires an explicit precedence decision or a narrowly scoped exception.",
        "- **EUR-Lex.** Use the CELEX sector and document-type letters or an ELI type. A proposal, regulation, directive, framework decision, parliamentary position and recommendation are different types. Domain-only guessing loses that distinction. Official-Journal references and Council-document identifiers without CELEX remain unknown.",
        "- **Generic links.** Information pages, the government homepage, videos and attachments without metadata do not identify a legal document type. The accented hostname `svenskförfattningssamling.se` is not the same hostname as `svenskforfattningssamling.se`; it is not silently treated as a trusted alias.",
        "- **Actors and dates.** Type inference does not establish who issued a legal act, what a chain date means, or whether a process is ongoing. Those findings need separate rules.",
        "- **Wrong targets of the right type.** A link to the wrong proposition or SFS document still matches the same URL rule. This approach does not replace the title/identifier and broken-link checks in the earlier reports.",
        "",
        f"Across all stages, {summary['mixed_stages']} contain confidently classified documents of different stage types, and {summary['heading_disagreements']} uniform stages have another type than their recognized heading. These are diagnostics, not counts of proven website errors. Full cases are retained in `chains-url-report.json`.",
        "",
        "Rules are isolated in `services/chains/normalization.py` and also used by the lean exporter. This audit itself changes no stored observations or exported chain data.",
        "",
        "Source definitions: [EUR-Lex CELEX numbers](https://eur-lex.europa.eu/content/help/eurlex-content/celex-number.html?locale=en), [EUR-Lex document types](https://eur-lex.europa.eu/content/tools/TableOfSectors/types_of_documents_in_eurlex.html?locale=en), [Riksdagen document types](https://www.riksdagen.se/sv/dokument-och-lagar/).",
        "",
        "Reproduce:",
        "",
        "```bash",
        "uv run python -m scripts.audit_chain_types",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--draft",
        type=Path,
        help="Optionally restrict the audit to exotic labels in a supplied draft",
    )
    parser.add_argument("--report", type=Path, default=Path("chains-url-report.json"))
    parser.add_argument(
        "--markdown", type=Path, default=Path("docs/chains-url-analysis.md")
    )
    args = parser.parse_args()
    report = analyse(args.data_dir, args.draft)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
