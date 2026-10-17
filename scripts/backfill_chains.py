"""Fetch historical chains: uv run python -m scripts.backfill_chains."""

import argparse
from pathlib import Path

from tqdm import tqdm

from fetch import export_types
from services.chains import ChainStore
from services.chains.export import publish_json
from services.chains.parser import normalize_url
from services.chains.records import apply_item_chain_references
from services.chains.reporting import (
    remove_published_reports,
    report_normalizations,
    write_local_reports,
)
from services.chains.types import ChainItem, ChainReport, WebpageDownloader
from services.downloader import Downloader
from services.reader import read_json
from services.redirecter import get_final_url


def backfill(
    items: list[ChainItem],
    store: ChainStore,
    downloader: WebpageDownloader,
    limit: int | None = None,
    offset: int = 0,
) -> int:
    selected = items[offset:][:limit]
    print(
        f"Backfill: {len(selected):,} pages, starting at offset {offset:,}.", flush=True
    )
    succeeded = 0
    with tqdm(total=len(selected), desc="Backfilling chains", unit="page") as progress:
        for attempted, item in enumerate(selected, start=1):
            try:
                html = downloader.get_webpage(item["url"])
            except Exception as error:
                store.failures.append({"source": item["url"], "error": str(error)})
            else:
                succeeded += store.fetch_views(
                    html, item["url"], downloader, get_final_url
                )
            progress.set_postfix(
                ok=succeeded, failed=attempted - succeeded, refresh=False
            )
            progress.update()
    return len(selected)


def recheck(
    report: ChainReport,
    store: ChainStore,
    downloader: WebpageDownloader,
    limit: int | None = None,
) -> set[str]:
    """Revisit exact views from an explicitly supplied local report."""
    sources = sorted({normalize_url(url, view=True) for url in report["recheck"]})
    pending = set(sources)
    selected = sources[:limit]
    with tqdm(total=len(selected), desc="Rechecking chains", unit="view") as progress:
        for source in selected:
            pending.remove(source)
            try:
                html = downloader.get_webpage(source)
            except Exception as error:
                store.failures.append({"source": source, "error": str(error)})
            else:
                store.observe(html, normalize_url(source), source, get_final_url)
            progress.update()
    store.failures.extend(
        f
        for f in report.get("failures", [])
        if normalize_url(f["source"], view=True) in pending
    )
    return pending


def print_summary(report: ChainReport) -> None:
    print(
        f"\nExported {report['chains']:,} chains; observed {report['observations']:,} source views this run."
    )
    print(
        f"Quality: {report['parser_failures']:,} fetch/parse failures, {report['ambiguous_matches']:,} ambiguous document matches, {report['conflicting_observations']:,} conflicts."
    )
    print(f"Source views for recheck: {len(report['recheck']):,}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--offset", type=int, default=0, help="Start at this position in items.json"
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Replace the collection using only this run's observations",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        help="Write optional local JSON and Markdown diagnostics",
    )
    parser.add_argument(
        "--recheck",
        type=Path,
        help="Revisit source views listed in a local quality report",
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.offset < 0:
        parser.error("--offset must be nonnegative")
    if args.recheck and (args.offset or args.fresh):
        parser.error("--recheck cannot be combined with --offset or --fresh")
    items = read_json("data/api/items.json")
    store = ChainStore() if args.fresh else ChainStore.from_file("data/api/chains.json")
    codes_path = Path("data/api/codes.json")
    codes = read_json(codes_path) if codes_path.exists() else {}
    downloader = Downloader()
    try:
        pending = set()
        if args.recheck:
            pending = recheck(read_json(args.recheck), store, downloader, args.limit)
        else:
            backfill(items, store, downloader, args.limit, args.offset)
        export = store.build_export(items, pending, codes=codes)
        apply_item_chain_references(items, export.item_references)
        files = {"api/items.json": items, "api/chains.json": export.collection}
        export_types(items, files)
        publish_json(files)
        remove_published_reports()
        print_summary(export.report)
        report_normalizations(export.normalization_report)
        if args.report_dir is not None:
            write_local_reports(
                export.report, export.normalization_report, args.report_dir
            )
            print(f"Local reports: {args.report_dir}")
    finally:
        downloader.b.close()


if __name__ == "__main__":
    main()
