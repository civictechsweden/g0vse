import os
from tqdm import tqdm

from services.downloader import Downloader
from services.reader import read_json
from services.timer import Timer
from services.writer import Writer
from services.web_parser import extract_page

OVERWRITE = False
ITEMS_PATH = "./data/api/items.json"
CODES_PATH = "./data/api/codes.json"
LATEST_UPDATED_PATH = "./data/api/latest_updated.json"


def prepare_items(downloader, timer):
    amount_online = downloader.get_amount()
    print(f"Found {amount_online} documents on regeringen.se")

    just_fetch_new = not OVERWRITE and os.path.exists(LATEST_UPDATED_PATH)

    if just_fetch_new:
        codes = read_json(CODES_PATH)
        items = read_json(ITEMS_PATH)
        items.reverse()

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
        new_items = [
            i
            for i in new_items
            if Downloader.last_updated(i) > timer.day_before()
            or (
                "/remisser/" in i["url"]
                and not i["updated"]
                and Downloader.last_updated(i) > timer.six_months_before()
            )
        ]
        new_items.reverse()
        new_urls = {item["url"] for item in new_items}

        print(f"Updating the content of {len(new_items)} pages...")

        items = [item for item in items if item["url"] not in new_urls]
        items.extend(new_items)
        items.reverse()
        codes.update(new_codes)
    else:
        items, codes = new_items, new_codes

    return items, codes


def process_item(item, downloader, codes, pbar=None):
    url = item["url"]
    md_path = "data/" + url.strip("/") + ".md"

    # Robust skip: check if MD exists AND item already has metadata (e.g., 'id')
    if not OVERWRITE and os.path.exists(md_path) and item.get("id"):
        return False

    if "attachments" in item or "201314184" in url:
        return False

    if pbar:
        pbar.set_description(f"Processing {url[:40]}...")
    else:
        print(f"Fetching page at {url}...")

    page = downloader.get_webpage(url)

    if not page:
        print(f"Error: {url}")
        return False

    md_content, metadata = extract_page(page)

    if not md_content:
        print(f"Error: {url}")
        return False

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

    # Write MD LAST. If this exists on next run, we know metadata is in memory.
    Writer.write_md(md_content, md_path)
    return True


def main():
    downloader = Downloader()
    timer = Timer()
    items, codes = prepare_items(downloader, timer)

    Writer.write_json(items, ITEMS_PATH)
    Writer.write_json(codes, CODES_PATH)

    processed_count = 0
    try:
        with tqdm(items, desc="Processing items", unit="item") as pbar:
            for i, item in enumerate(pbar):
                if process_item(item, downloader, codes, pbar=pbar):
                    processed_count += 1

                # Periodically save progress to avoid losing everything
                if (i + 1) % 1000 == 0:
                    Writer.write_json(items, ITEMS_PATH)
                    Writer.write_json(codes, CODES_PATH)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving progress...")
    except Exception as e:
        print(f"\nCrash detected: {e}")
        print("Saving current progress and attempting to finalize...")
    finally:
        # Final save of the current state
        Writer.write_json(items, ITEMS_PATH)
        Writer.write_json(codes, CODES_PATH)

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

    types = read_json("./frontend/types.json")

    def get_by_type(type, items):
        return [item for item in items if f"/{type}/" in item["url"]]

    for type in tqdm(types, desc="Exporting types", unit="type"):
        Writer.write_json(get_by_type(type, items), f"./data/{type}.json")


if __name__ == "__main__":
    main()
