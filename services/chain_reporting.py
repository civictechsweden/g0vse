"""Bounded Actions summary and complete downloadable normalization evidence."""

import html
import json
import os
from pathlib import Path
from urllib.parse import quote

from services.chain_types import NormalizationFinding, NormalizationReport

REPORT_PATH = Path("data/api/chains-normalization.json")
ISSUE_LABELS = {
    "normalized_stage": "Stage name normalized",
    "split_stage": "Mixed stage split",
    "unresolved_stage": "Unresolved stage name",
    "stage_type_disagreement": "Stage/document type mismatch",
    "document_type_conflict": "URL/item type mismatch",
    "date_discrepancy": "Chain/item date discrepancy",
    "actor_group": "Actor/group heading",
}


def previous_normalizations(path: Path = REPORT_PATH) -> NormalizationReport | None:
    return json.loads(path.read_text()) if path.exists() else None


def cell(value: object, limit: int = 160) -> str:
    if isinstance(value, list):
        text = ", ".join(str(v) for v in value)
    else:
        text = str(value) if value is not None else "—"
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return html.escape(text).replace("|", "\\|")


def finding_row(finding: NormalizationFinding) -> str:
    source = finding["source"]
    if source.startswith("/"):
        source = "https://www.regeringen.se" + source
    source = quote(source, safe=":/?&=%;+#")
    description = finding["document_title"] or finding["reason"]
    return (
        f"| {cell(finding['departments'] or ['Ej angivet'])} | [page](<{source}>) "
        f"| {cell(ISSUE_LABELS.get(finding['kind'], finding['kind']))} | {cell(description)} "
        f"| {cell(finding['before'])} | {cell(finding['after'])} |"
    )


def render_normalization_report(
    report: NormalizationReport,
    previous: NormalizationReport | None = None,
    *,
    max_rows: int | None = None,
    max_bytes: int | None = None,
) -> str:
    before = {f["id"] for f in previous["findings"]} if previous else set()
    current = {f["id"] for f in report["findings"]}
    summary = report["summary"]
    lines = [
        "## Legislative chain normalization",
        "",
        f"Normalized **{summary.get('normalized_stages', 0):,}** nonstandard stages; "
        f"split **{summary.get('split_stages', 0):,}** mixed stages. "
        f"**{summary.get('reviews', 0):,}** findings need review.",
        "",
        f"New findings: **{len(current - before):,}**. "
        f"No longer observed: **{len(before - current):,}**. "
        "These comparisons use stored observations; they are not a fresh check of every page.",
        "",
        "Type mappings standardize the vocabulary. Review findings are not automatic corrections. "
        "Chain dates and actor/group headings remain unchanged. A missing department is shown explicitly.",
        "",
        "Full evidence: `api/chains-normalization.json` and the `chain-normalization` workflow artifact. "
        "`uv run backfill_chains.py --recheck` revisits the affected source views.",
        "",
    ]
    lines += ["| Issue | Findings |", "| --- | ---: |"]
    lines.extend(
        f"| {label} | {summary[kind]:,} |"
        for kind, label in ISSUE_LABELS.items()
        if summary.get(kind)
    )
    lines += [
        "",
        "| Department | Source | Issue | Description | Observed | Suggested |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    findings = sorted(
        report["findings"],
        key=lambda f: (
            f["id"] in before,
            f["status"] != "normalized",
            f["departments"],
            f["kind"],
            f["before"] or "",
            f["id"],
        ),
    )
    patterns = set()
    shown = 0
    for finding in findings:
        # The short summary illustrates different problems; the full artifact
        # keeps one row per finding/chain, never one row per source view.
        pattern = json.dumps(
            [
                finding["departments"],
                finding["kind"],
                finding["before"],
                finding["after"],
            ],
            ensure_ascii=False,
        )
        if max_rows is not None and pattern in patterns:
            continue
        row = finding_row(finding)
        if max_rows is not None and shown >= max_rows:
            break
        if (
            max_bytes is not None
            and len(("\n".join(lines) + row).encode()) > max_bytes - 400
        ):
            break
        lines.append(row)
        patterns.add(pattern)
        shown += 1
    if shown < len(findings):
        lines += [
            "",
            f"Showing {shown:,} examples of {len(findings):,} findings. Download the artifact for the complete list.",
        ]
    if not findings:
        lines += ["", "No normalization findings in the stored observations."]
    return "\n".join(lines) + "\n"


def report_normalizations(
    report: NormalizationReport, previous: NormalizationReport | None = None
) -> None:
    summary = report["summary"]
    print(
        f"Normalization: {summary.get('normalized_stages', 0):,} stages mapped, "
        f"{summary.get('split_stages', 0):,} split; "
        f"{summary.get('reviews', 0):,} findings for review."
    )
    print(f"Normalization evidence: {REPORT_PATH}")
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(path).open("a", encoding="utf-8") as output:
            output.write(
                render_normalization_report(
                    report, previous, max_rows=20, max_bytes=40_000
                )
            )
    if os.environ.get("GITHUB_ACTIONS") == "true" and (
        temporary := os.environ.get("RUNNER_TEMP")
    ):
        directory = Path(temporary) / "chain-normalization"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "normalization.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )
        (directory / "normalization.md").write_text(
            render_normalization_report(report, previous)
        )
