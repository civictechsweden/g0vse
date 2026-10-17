"""Collect this run's observations and update the published chain collection."""

import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path

from services.chains.enrichment import (
    enrich_remiss_memberships,
    without_inferred_memberships,
)
from services.chains.merge import item_references, merge_collections
from services.chains.normalization import normalize_chain_records
from services.chains.parser import extract_chains, normalize_url
from services.chains.reconciliation import assign_public_ids, reconcile_identities
from services.chains.records import build_chain_records, build_chain_report
from services.chains.types import (
    ChainCollection,
    ChainItem,
    ChainReport,
    Failure,
    ItemReferences,
    NormalizationReport,
    Observation,
    RedirectResolver,
    WebpageDownloader,
)


@dataclass(frozen=True)
class ChainExport:
    collection: ChainCollection
    report: ChainReport
    item_references: ItemReferences
    normalization_report: NormalizationReport


class ChainStore:
    def __init__(self, baseline: ChainCollection | None = None):
        self.baseline: ChainCollection = (
            baseline if baseline is not None else {"chains": {}}
        )
        self.observations: dict[str, Observation] = {}
        self.redirects: dict[str, str] = {}
        self.failures: list[Failure] = []

    @classmethod
    def from_file(cls, path: str | Path) -> "ChainStore":
        path = Path(path)
        if not path.exists():
            return cls()
        collection = json.loads(path.read_text())
        if collection.get("version") == 1:
            raise ValueError(
                "Legacy chains.json: run uv run python -m scripts.backfill_chains --fresh to build the lean format"
            )
        return cls({"chains": collection["chains"]})

    def observe(
        self,
        html: str | None,
        item_url: str,
        source_view_url: str | None = None,
        resolve: RedirectResolver | None = None,
    ) -> list[str] | None:
        source_view_url = normalize_url(source_view_url or item_url, view=True)

        def cached_resolve(url: str) -> str:
            if url not in self.redirects:
                if resolve is None:
                    raise ValueError(f"No redirect resolver for {url}")
                target = resolve(url)
                normalize_url(target)  # Do not cache an unresolved/invalid redirect.
                self.redirects[url] = target
            return self.redirects[url]

        try:
            if not html:
                raise ValueError("Fetch returned no HTML")
            observation, choices = extract_chains(
                html, item_url, source_view_url, cached_resolve
            )
        except Exception as error:
            self.failures.append({"source": source_view_url, "error": str(error)})
            return None
        self.observations[source_view_url] = observation
        return choices

    def fetch_views(
        self,
        html: str | None,
        item_url: str,
        downloader: WebpageDownloader,
        resolve: RedirectResolver | None,
    ) -> bool:
        """Each selector is independently replaceable; failure retains its old view."""
        queue = [(item_url, html)]
        seen = set()
        success = True
        while queue:
            source_view_url, page = queue.pop(0)
            source_view_url = normalize_url(source_view_url, view=True)
            if source_view_url in seen:
                continue
            seen.add(source_view_url)
            if page is None and source_view_url != normalize_url(item_url, view=True):
                try:
                    page = downloader.get_webpage(source_view_url)
                except Exception as error:
                    self.failures.append(
                        {"source": source_view_url, "error": str(error)}
                    )
                    success = False
                    continue
            choices = self.observe(page, item_url, source_view_url, resolve)
            if choices is None:
                success = False
            else:
                queue.extend((choice, None) for choice in choices if choice not in seen)
        return success

    def build_export(
        self,
        items: list[ChainItem],
        pending_source_views: Iterable[str] = (),
        *,
        codes: dict[str, str] | None = None,
        normalize: bool = True,
    ) -> ChainExport:
        """Assemble and normalize fresh views, then update the published baseline.

        Neither items, the baseline nor source observations are mutated.
        Historical views are preserved only through their public chain records.
        """
        baseline = without_inferred_memberships(self.baseline)
        groups = reconcile_identities(self.observations)
        public_ids = assign_public_ids(groups, baseline, items)
        records = build_chain_records(groups, items, public_ids)
        normalizations: NormalizationReport = (
            normalize_chain_records(
                records.collection, records.evidence, items, codes or {}
            )
            if normalize
            else {"version": 1, "summary": {}, "findings": [], "recheck": []}
        )
        collection = merge_collections(baseline, records.collection)
        inferred = enrich_remiss_memberships(collection, items, codes or {})
        previous_references = item_references(self.baseline)
        normalizations["findings"].extend(inferred)
        normalizations["summary"]["findings"] = len(normalizations["findings"])
        normalizations["summary"]["inferred_remiss"] = len(inferred)
        normalizations["summary"]["new_inferred_remisses"] = sum(
            finding["chain"]
            not in previous_references.get(normalize_url(finding["source"]), set())
            for finding in inferred
        )
        references = item_references(collection)
        records = replace(records, collection=collection, item_references=references)
        report = build_chain_report(
            records,
            self.failures,
            len(self.observations),
            set(pending_source_views) | set(normalizations["recheck"]),
        )
        report["normalization"] = normalizations["summary"]
        return ChainExport(collection, report, references, normalizations)
