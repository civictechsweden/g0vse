"""Persistent source observations and conservative, reproducible reconciliation."""

import json
import os
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from services.chain_parser import extract_chains, normalize_url
from services.chain_reconciliation import reconcile_identities
from services.chain_records import build_chain_records, build_chain_report
from services.chain_types import (
    Assignments,
    ChainCollection,
    ChainItem,
    ChainReport,
    ChainState,
    Failure,
    ItemReferences,
    RedirectResolver,
    WebpageDownloader,
)


@dataclass(frozen=True)
class ChainExport:
    collection: ChainCollection
    report: ChainReport
    item_references: ItemReferences
    assignments: Assignments


class ChainStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.state: ChainState = {
            "version": 1,
            "observations": {},
            "assignments": {},
            "aliases": {},
            "redirects": {},
            "completed": [],
        }
        if self.path and self.path.exists():
            self.state = json.loads(self.path.read_text())
            if self.state["version"] != 1:
                raise ValueError("Unsupported chain state version")
        self.failures: list[Failure] = []

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=4, sort_keys=True) + "\n"
        )
        os.replace(temporary, self.path)

    def observe(
        self,
        html: str | None,
        item_url: str,
        source_view_url: str | None = None,
        resolve: RedirectResolver | None = None,
    ) -> list[str] | None:
        source_view_url = normalize_url(source_view_url or item_url, view=True)

        def cached_resolve(url: str) -> str:
            if url not in self.state["redirects"]:
                if resolve is None:
                    raise ValueError(f"No redirect resolver for {url}")
                target = resolve(url)
                normalize_url(target)  # Do not cache an unresolved/invalid redirect.
                self.state["redirects"][url] = target
            return self.state["redirects"][url]

        try:
            if not html:
                raise ValueError("Fetch returned no HTML")
            observation, choices = extract_chains(
                html, item_url, source_view_url, cached_resolve
            )
        except Exception as error:
            self.failures.append({"source": source_view_url, "error": str(error)})
            return None
        self.state["observations"][source_view_url] = observation
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
    ) -> ChainExport:
        """Build public data without mutating items or stored identity history."""
        reconciliation = reconcile_identities(
            self.state["observations"],
            self.state["assignments"],
            self.state["aliases"],
        )
        records = build_chain_records(
            reconciliation.groups, reconciliation.aliases, items
        )
        report = build_chain_report(
            records,
            self.failures,
            len(self.state["observations"]),
            pending_source_views,
        )
        return ChainExport(
            records.collection,
            report,
            records.item_references,
            reconciliation.assignments,
        )

    def update_identity_history(self, export: ChainExport) -> None:
        """Remember IDs and aliases after the corresponding export is published."""
        self.state["assignments"] = deepcopy(export.assignments)
        self.state["aliases"] = deepcopy(export.collection["aliases"])
