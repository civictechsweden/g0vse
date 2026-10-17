"""Collect reproducible normalization findings with original source evidence."""

from collections import Counter
from dataclasses import dataclass

from services.chain_parser import digest, normalize_url
from services.chain_types import (
    ChainItem,
    NormalizationFinding,
    NormalizationReport,
    PublishedDocument,
)


@dataclass(frozen=True)
class FindingContext:
    chain: str
    phase: str | None
    actor: str | None
    stage: str | None = None


class NormalizationLog:
    def __init__(self, items: dict[str, ChainItem], codes: dict[str, str]):
        self.items = items
        self.codes = codes
        self.findings: dict[str, NormalizationFinding] = {}
        self.recheck: set[str] = set()
        self.normalized_stages = 0
        self.split_stages = 0

    def departments(self, source: str) -> list[str]:
        item = self.items.get(normalize_url(source), {})
        return sorted(
            {
                self.codes[code]
                for code in item.get("senders", [])
                if code in self.codes
                and (
                    self.codes[code].endswith("departementet")
                    or self.codes[code] == "Statsrådsberedningen"
                )
            }
        )

    def add(
        self,
        context: FindingContext,
        kind: str,
        before: str | None,
        after: str | list[str] | None,
        reason: str,
        documents: list[PublishedDocument],
        *,
        status: str = "review",
    ) -> None:
        sources = {source for doc in documents for source in doc["sources"]}
        self.recheck.update(sources)
        urls = sorted({doc["url"] for doc in documents})
        # A new source view or a growing stage is still the same label issue.
        # Document-specific findings distinguish individual links/dates.
        identity = [
            context.chain,
            kind,
            context.phase,
            context.actor,
            context.stage,
            before,
            after,
            urls if kind in {"date_discrepancy", "document_type_conflict"} else [],
        ]
        finding_id = digest(identity)[:16]
        previous = self.findings.get(finding_id)
        if previous:
            sources.add(previous["source"])
            urls = sorted(set(urls) | set(previous["documents"]))
        source = max(
            sources,
            key=lambda url: (
                bool(self.departments(url)),
                self.items.get(normalize_url(url), {}).get("published") or "",
                url,
            ),
        )
        self.findings[finding_id] = {
            "id": finding_id,
            "chain": context.chain,
            "phase": context.phase,
            "actor": context.actor,
            "stage": context.stage,
            "kind": kind,
            "status": status,
            "before": before,
            "after": after,
            "reason": reason,
            "documents": urls,
            "document_title": self.items.get(normalize_url(urls[0]), {}).get("title")
            if len(urls) == 1
            else None,
            "source": source,
            "departments": self.departments(source),
        }

    def report(self) -> NormalizationReport:
        findings = sorted(
            self.findings.values(),
            key=lambda f: (f["kind"], f["before"] or "", f["chain"], f["id"]),
        )
        counts = Counter(f["kind"] for f in findings)
        return {
            "version": 1,
            "summary": {
                "normalized_stages": self.normalized_stages,
                "split_stages": self.split_stages,
                "findings": len(findings),
                "reviews": sum(f["status"] == "review" for f in findings),
                **dict(sorted(counts.items())),
            },
            "findings": findings,
            "recheck": sorted(self.recheck),
        }
