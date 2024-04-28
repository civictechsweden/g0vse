import json
from datetime import datetime
from zoneinfo import ZoneInfo
import os

from services.downloader import Downloader
from services.writer import Writer

OVERWRITE = False
ITEMS_PATH = "./api/items.json"
CODES_PATH = "./api/codes.json"

downloader = Downloader()
amount_online = downloader.get_amount()
to_fetch = amount_online
print(f"Found {amount_online} documents on regeringen.se")

just_fetch_new = not OVERWRITE and os.path.exists(ITEMS_PATH)

if just_fetch_new:
    with open(ITEMS_PATH, "r") as file:
        items = json.load(file)

    items.reverse()
    amount_saved = len(items)

    with open(CODES_PATH, "r") as file:
        codes = json.load(file)

    print(f"Found {amount_saved} existing items.")
    print(f"Found {len(codes)} existing codes.")

    to_fetch = abs(amount_online - amount_saved) + 10

now = datetime.now(ZoneInfo("Europe/Stockholm")).strftime("%Y-%m-%d %H:%M:%S")
new_items, new_codes = downloader.get_latest_items(to_fetch)

if just_fetch_new:
    new_items.reverse()
    new_codes = {str(key): new_codes[key] for key in sorted(new_codes)}
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

metadata = {"latest_updated": now, "items": len(items), "codes": len(codes)}

Writer.write_json(items, ITEMS_PATH)
Writer.write_json(codes, CODES_PATH)
Writer.write_json(metadata, "./api/latest_updated.json")
