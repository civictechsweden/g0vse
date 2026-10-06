"""Resumable backfill: uv run backfill_chains.py [--limit N] [--retry]."""

import argparse
from pathlib import Path

from fetch import export_types
from services.chain_export import publish_json
from services.chain_parser import normalize_url
from services.chain_records import apply_item_chain_references
from services.chain_types import ChainItem, ChainReport, WebpageDownloader
from services.chains import ChainStore
from services.downloader import Downloader
from services.reader import read_json
from services.redirecter import get_final_url


def backfill(
    items: list[ChainItem],
    store: ChainStore,
    downloader: WebpageDownloader,
    limit: int | None = None,
    retry: bool = False,
) -> int:
    completed = set(store.state["completed"])
    attempted = 0
    try:
        for item in items:
            url = item["url"]
            if url in completed and not retry:
                continue
            if limit is not None and attempted >= limit:
                break
            attempted += 1
            try:
                html = downloader.get_webpage(url)
            except Exception as error:
                store.failures.append({"source": url, "error": str(error)})
                continue
            if store.fetch_views(html, url, downloader, get_final_url):
                completed.add(url)
            if attempted % 100 == 0:
                store.state["completed"] = sorted(completed)
                store.save()
    finally:
        store.state["completed"] = sorted(completed)
        store.save()
    return attempted


def recheck(
    report: ChainReport,
    store: ChainStore,
    downloader: WebpageDownloader,
    limit: int | None = None,
) -> set[str]:
    """Refresh exact queued views and retain failures not reached by this run."""
    source_view_urls = sorted(
        {normalize_url(url, view=True) for url in report["recheck"]}
    )
    pending_source_views = set(source_view_urls)
    try:
        for attempted, source_view_url in enumerate(source_view_urls[:limit], start=1):
            pending_source_views.remove(source_view_url)
            try:
                html = downloader.get_webpage(source_view_url)
            except Exception as error:
                store.failures.append({"source": source_view_url, "error": str(error)})
            else:
                store.observe(
                    html, normalize_url(source_view_url), source_view_url, get_final_url
                )
            if attempted % 100 == 0:
                store.save()
    finally:
        store.save()
    # With [A, B] queued and limit=1, A gets a fresh result while B keeps its
    # previous failure. Dropping B here would make the next recheck forget it.
    store.failures.extend(
        failure
        for failure in report.get("failures", [])
        if normalize_url(failure["source"], view=True) in pending_source_views
    )
    return pending_source_views


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--retry", action="store_true", help="Refresh even completed pages"
    )
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="Retry sources queued in the last build report",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    items = read_json("data/api/items.json")
    store = ChainStore(Path("data/.chain-state/state.json"))
    downloader = Downloader()
    try:
        pending_source_views = set()
        if args.recheck:
            report = read_json("data/api/chains-report.json")
            pending_source_views = recheck(report, store, downloader, args.limit)
        else:
            backfill(items, store, downloader, args.limit, args.retry)
        chain_export = store.build_export(items, pending_source_views)
        apply_item_chain_references(items, chain_export.item_references)
        files = {
            "api/items.json": items,
            "api/chains.json": chain_export.collection,
            "api/chains-report.json": chain_export.report,
        }
        export_types(items, files)
        publish_json(files)
        store.update_identity_history(chain_export)
        store.save()
        print(chain_export.report)
    finally:
        downloader.b.close()


if __name__ == "__main__":
    main()
