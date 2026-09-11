import errno
import gc
import os
from enum import Enum
from pathlib import Path

from tqdm import tqdm

from services.downloader import Downloader
from services.item_refresh import (
    RefreshPlan,
    plan_incremental_refresh,
    promote_changed_items,
)
from services.reader import read_json
from services.timer import Timer
from services.web_parser import extract_page
from services.writer import Writer

OVERWRITE = False
ITEMS_PATH = "./data/api/items.json"
CODES_PATH = "./data/api/codes.json"
LATEST_UPDATED_PATH = "./data/api/latest_updated.json"


class ProcessingOutcome(Enum):
    SKIPPED = "skipped"
    FAILED = "failed"
    UNCHANGED = "unchanged"
    CHANGED = "changed"


def should_refresh_item(item, timer):
    """Select recent pages plus remiss pages that need defensive refreshing."""
    last_updated = Downloader.last_updated(item)
    return last_updated > timer.day_before() or (
        "/remisser/" in item["url"]
        and not item["updated"]
        and last_updated > timer.six_months_before()
    )


def prepare_items(downloader, timer):
    amount_online = downloader.get_amount()
    print(f"Found {amount_online} documents on regeringen.se")

    just_fetch_new = not OVERWRITE and os.path.exists(LATEST_UPDATED_PATH)

    if just_fetch_new:
        codes = read_json(CODES_PATH)
        items = read_json(ITEMS_PATH)

        stats = read_json(LATEST_UPDATED_PATH)
        timer.set_latest_update(stats["latest_updated"])
        amount_saved = stats["items"]

        print(f"Found {amount_saved} existing items.")
        print(f"Found {len(codes)} existing codes.")

        delta = timer.get_delta()
        to_fetch = abs(amount_online - amount_saved) + 10 + 12 * (delta + 180 - 1)
    else:
        codes = {}
        items = []
        to_fetch = amount_online

    print(f"Fetching the latest {to_fetch} items...")
    new_items, new_codes = downloader.get_latest_items(to_fetch)

    if just_fetch_new:
        refresh_candidates = [
            item for item in new_items if should_refresh_item(item, timer)
        ]

        print(f"Updating the content of {len(refresh_candidates)} pages...")

        items, refresh_plan = plan_incremental_refresh(items, refresh_candidates)
        codes.update(new_codes)
    else:
        items, codes = new_items, new_codes
        refresh_plan = RefreshPlan()

    return items, codes, refresh_plan


def process_item(
    item,
    downloader,
    codes,
    existing_mds=None,
    pbar=None,
    force_refresh=False,
    previous_item=None,
):
    url = item["url"]
    md_rel_path = url.strip("/") + ".md"

    # Optimization: Use pre-scanned set instead of os.path.exists
    is_existing = (
        md_rel_path in existing_mds
        if existing_mds is not None
        else os.path.exists(f"data/{md_rel_path}")
    )

    if "201314184" in url:
        return ProcessingOutcome.SKIPPED

    if not force_refresh and (
        (not OVERWRITE and is_existing and item.get("id")) or "attachments" in item
    ):
        return ProcessingOutcome.SKIPPED

    if pbar:
        pbar.set_description(f"Processing {url[:40]}...")
    else:
        print(f"Fetching page at {url}...")

    page = downloader.get_webpage(url)

    if not page:
        print(f"Error: {url}")
        return ProcessingOutcome.FAILED

    md_content, metadata = extract_page(page, url)
    del page  # Explicitly free memory for the large HTML string

    if not md_content:
        print(f"Error: {url}")
        return ProcessingOutcome.FAILED

    comparison_item = previous_item if previous_item is not None else item.copy()

    # Update global codes mapping
    labels = metadata.pop("labels", {})
    for code, name in labels.items():
        codes[code] = name

    # Update item with metadata
    if metadata.get("title"):
        item["title"] = metadata["title"]

    # Filter categories to avoid duplicates with types/senders
    metadata["categories"] = [
        c for c in metadata["categories"] if c not in item["types"] + item["senders"]
    ]
    item.update(metadata)

    normalized_markdown = Writer.normalize_md(md_content)
    item_changed = item != comparison_item
    markdown_changed = True
    if not item_changed and is_existing:
        markdown_path = Path(f"data/{md_rel_path}")
        markdown_changed = (
            Writer.normalize_md(markdown_path.read_text(encoding="utf-8"))
            != normalized_markdown
        )

    if item_changed or markdown_changed:
        # Write Markdown last. Its presence tells later runs that parsing succeeded.
        try:
            Writer.write_md(normalized_markdown, f"data/{md_rel_path}")
        except OSError as e:
            if e.errno != errno.ENAMETOOLONG:
                raise

            # A few slugs exceed the filesystem's per-component limit. Keep
            # their parsed metadata even though Markdown cannot be represented.
            print(f"Skipping Markdown with overlong filename: {url}")

    return (
        ProcessingOutcome.CHANGED
        if item_changed or markdown_changed
        else ProcessingOutcome.UNCHANGED
    )


def process_all_items(items, downloader, codes, refresh_plan=None):
    refresh_plan = refresh_plan or RefreshPlan()
    # Pre-scan existing Markdown files to avoid thousands of syscalls
    existing_mds = set()
    if os.path.exists("data/"):
        for root, _, files in os.walk("data/"):
            for file in files:
                if file.endswith(".md"):
                    rel_path = os.path.relpath(os.path.join(root, file), "data/")
                    existing_mds.add(rel_path)

    processed_count = 0
    changed_refresh_urls = set(refresh_plan.new_urls)
    try:
        with tqdm(items, desc="Processing items", unit="item") as pbar:
            for i, item in enumerate(pbar):
                url = item["url"]
                force_refresh = url in refresh_plan.force_refresh_urls
                previous_item = refresh_plan.previous_items.get(url)
                outcome = process_item(
                    item,
                    downloader,
                    codes,
                    existing_mds=existing_mds,
                    pbar=pbar,
                    force_refresh=force_refresh,
                    previous_item=previous_item,
                )

                if (
                    force_refresh
                    and outcome
                    in {
                        ProcessingOutcome.FAILED,
                        ProcessingOutcome.SKIPPED,
                    }
                    and previous_item is not None
                ):
                    # A failed refresh must never replace a complete stored object.
                    items[i] = previous_item

                if force_refresh and outcome is ProcessingOutcome.CHANGED:
                    changed_refresh_urls.add(url)

                if outcome in {
                    ProcessingOutcome.CHANGED,
                    ProcessingOutcome.UNCHANGED,
                }:
                    processed_count += 1
                    if processed_count % 1000 == 0:
                        Writer.write_json(items, ITEMS_PATH)
                        Writer.write_json(codes, CODES_PATH)

                # Periodically trigger garbage collection to free fragmented memory
                if (i + 1) % 500 == 0:
                    gc.collect()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving progress...")
    except Exception as e:
        print(f"\nCrash detected: {e}")
        # Do not finalize and publish partially parsed search results. A later
        # run can retry them, while the last complete data export stays live.
        raise

    return promote_changed_items(
        items, refresh_plan.candidate_order, changed_refresh_urls
    )


def finalize_data(items, codes, timer):
    print("Finalizing data...")
    codes = {str(key): codes[key] for key in sorted(codes)}

    latest_updated = {
        "latest_updated": timer.start_string(),
        "items": len(items),
        "codes": len(codes),
    }

    Writer.write_json(items, ITEMS_PATH)
    Writer.write_json(codes, CODES_PATH)
    Writer.write_json(latest_updated, LATEST_UPDATED_PATH)


def export_types(items):
    types = read_json("./frontend/types.json")
    types_set = set(types)
    type_buckets = {t: [] for t in types}

    for item in tqdm(items, desc="Binning items by type", unit="item"):
        url_parts = item["url"].strip("/").split("/")
        current_prefix = ""
        for part in url_parts:
            current_prefix = f"{current_prefix}/{part}" if current_prefix else part
            if current_prefix in types_set:
                type_buckets[current_prefix].append(item)

    for t, bucket_items in tqdm(
        type_buckets.items(), desc="Exporting types", unit="type"
    ):
        Writer.write_json(bucket_items, f"./data/{t}.json")


def main():
    downloader = Downloader()
    timer = Timer()
    try:
        items, codes, refresh_plan = prepare_items(downloader, timer)

        Writer.write_json(items, ITEMS_PATH)
        Writer.write_json(codes, CODES_PATH)

        items = process_all_items(items, downloader, codes, refresh_plan)

        finalize_data(items, codes, timer)
        export_types(items)
    finally:
        downloader.b.close()


if __name__ == "__main__":
    main()
