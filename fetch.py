import json
import os

from services.downloader import Downloader
from services.reader import read_json
from services.timer import Timer
from services.writer import Writer
from services.web_parser import extract_page

OVERWRITE = False
ITEMS_PATH = "./api/items.json"
CODES_PATH = "./api/codes.json"

downloader = Downloader()
amount_online = downloader.get_amount()
to_fetch = amount_online
print(f"Found {amount_online} documents on regeringen.se")

just_fetch_new = not OVERWRITE and os.path.exists(ITEMS_PATH)

timer = Timer()

if just_fetch_new:
    codes = read_json(CODES_PATH)
    items = read_json(ITEMS_PATH)
    items.reverse()

    stats = read_json("./api/latest_updated.json")
    timer.set_latest_update(stats["latest_updated"])
    amount_saved = stats["items"]

    print(f"Found {amount_saved} existing items.")
    print(f"Found {len(codes)} existing codes.")

    delta = timer.get_delta()
    to_fetch = abs(amount_online - amount_saved) + 10 + 5 * (delta - 1)

print(f"Fetching the latest {to_fetch} items...")
new_items, new_codes = downloader.get_latest_items(to_fetch)
new_items = [i for i in new_items if Downloader.last_updated(i) > timer.day_before()]

for new_item in new_items:
    url = new_item["url"]

    print(f"Fetching page at {url}...")
    page = downloader.get_webpage(url)
    md_content, metadata = extract_page(page)
    Writer.write_md(md_content, "data/" + new_item["url"].strip("/") + ".md")
    new_item.update(metadata)

    # Lots the category here, only kept the ID!
    for category in metadata["categories"]:
        new_codes[str(category)] = category[1]

if just_fetch_new:
    new_items.reverse()
    new_urls = [item["url"] for item in new_items]

    to_remove = []

    for i, item in enumerate(items):
        if item["url"] in new_urls:
            to_remove.append(i)

    for i in sorted(to_remove, reverse=True):
        items.pop(i)

    items.extend(new_items)
    items.reverse()
    codes.update(new_codes)
else:
    items, codes = new_items, new_codes

codes = {str(key): codes[key] for key in sorted(codes)}

latest_updated = {
    "latest_updated": timer.start_string(),
    "items": len(items),
    "codes": len(codes),
}

Writer.write_json(items, ITEMS_PATH)
Writer.write_json(codes, CODES_PATH)
Writer.write_json(latest_updated, "./api/latest_updated.json")
