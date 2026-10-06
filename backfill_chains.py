"""Resumable backfill: uv run backfill_chains.py [--limit N] [--retry]."""

import argparse
from pathlib import Path

from tqdm import tqdm

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
    eligible = sum(retry or item["url"] not in completed for item in items)
    planned = eligible if limit is None else min(eligible, limit)
    print(
        f"Backfill: {eligible:,} eligible pages; attempting up to {planned:,} this run.",
        flush=True,
    )
    attempted = 0
    succeeded = 0
    try:
        with tqdm(total=planned, desc="Backfilling chains", unit="page") as progress:
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
                else:
                    if store.fetch_views(html, url, downloader, get_final_url):
                        completed.add(url)
                        succeeded += 1
                progress.set_postfix(
                    ok=succeeded, failed=attempted - succeeded, refresh=False
                )
                progress.update()
                if attempted % 100 == 0:
                    store.state["completed"] = sorted(completed)
                    store.save()
            # Duplicate URLs can become completed during this run and be skipped.
            progress.total = attempted
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
    selected_source_views = source_view_urls[:limit]
    print(
        f"Recheck: {len(source_view_urls):,} queued source views; "
        f"attempting {len(selected_source_views):,} this run.",
        flush=True,
    )
    succeeded = 0
    try:
        with tqdm(
            total=len(selected_source_views), desc="Rechecking chains", unit="view"
        ) as progress:
            for attempted, source_view_url in enumerate(selected_source_views, start=1):
                pending_source_views.remove(source_view_url)
                try:
                    html = downloader.get_webpage(source_view_url)
                except Exception as error:
                    store.failures.append(
                        {"source": source_view_url, "error": str(error)}
                    )
                else:
                    choices = store.observe(
                        html,
                        normalize_url(source_view_url),
                        source_view_url,
                        get_final_url,
                    )
                    succeeded += choices is not None
                progress.set_postfix(
                    ok=succeeded, failed=attempted - succeeded, refresh=False
                )
                progress.update()
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


def print_summary(report: ChainReport) -> None:
    print(
        f"\nExported {report['chains']:,} chains from {report['observations']:,} source views."
    )
    print(
        f"Quality: {report['parser_failures']:,} fetch/parse failures, "
        f"{report['ambiguous_matches']:,} ambiguous document matches, "
        f"{report['conflicting_observations']:,} conflicts."
    )
    print(f"Queued for recheck: {len(report['recheck']):,} source views.")
    print("Detailed report: data/api/chains-report.json")
    print("Checkpoint saved: data/.chain-state/state.json")


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
    print("Loading page index and chain checkpoints...", flush=True)
    items = read_json("data/api/items.json")
    store = ChainStore(Path("data/.chain-state/state.json"))
    print(f"Loaded {len(items):,} pages. Starting browser...", flush=True)
    downloader = Downloader()
    try:
        pending_source_views = set()
        if args.recheck:
            report = read_json("data/api/chains-report.json")
            pending_source_views = recheck(report, store, downloader, args.limit)
            attempted = len(report["recheck"]) - len(pending_source_views)
            print(f"Rechecked {attempted:,} source views this run.", flush=True)
        else:
            attempted = backfill(items, store, downloader, args.limit, args.retry)
            item_urls = {item["url"] for item in items}
            completed = item_urls & set(store.state["completed"])
            print(
                f"Attempted {attempted:,} pages this run. "
                f"Checkpoint: {len(completed):,}/{len(item_urls):,} pages completed; "
                f"{len(item_urls - completed):,} remaining.",
                flush=True,
            )
        print("Building chain records and quality report...", flush=True)
        chain_export = store.build_export(items, pending_source_views)
        apply_item_chain_references(items, chain_export.item_references)
        files = {
            "api/items.json": items,
            "api/chains.json": chain_export.collection,
            "api/chains-report.json": chain_export.report,
        }
        print("Publishing item, type, chain and report files...", flush=True)
        export_types(items, files)
        publish_json(files)
        store.update_identity_history(chain_export)
        store.save()
        print_summary(chain_export.report)
    finally:
        downloader.b.close()


if __name__ == "__main__":
    main()
