import json
import os

import requests

from services.downloader import Downloader
from services.web_parser import extract_page


def save_comparisons():
    with open("tests/test_cases.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    downloader = Downloader()

    # Create directories
    os.makedirs("tests/live", exist_ok=True)
    os.makedirs("tests/api", exist_ok=True)

    for i, case in enumerate(cases):
        url = case["url"]
        clean_url = url.strip("/")
        # Create a safe filename from the URL
        filename = clean_url.replace("/", "_")
        if not filename:
            filename = "index"

        api_md_url = f"https://g0v.se/{clean_url}.md"

        print(f"[{i + 1}/{len(cases)}] Processing {url}...")

        # 1. Get live MD from current parser and save
        html = downloader.get_webpage(url)
        if html:
            live_md, _ = extract_page(html)
            if live_md:
                with open(f"tests/live/{filename}.md", "w", encoding="utf-8") as f:
                    f.write(live_md)
            else:
                print(f"  FAILED to parse live HTML for {url}")
        else:
            print(f"  FAILED to fetch live HTML for {url}")

        # 2. Get stored MD from API and save
        try:
            response = requests.get(api_md_url)
            if response.status_code == 200:
                with open(f"tests/api/{filename}.md", "w", encoding="utf-8") as f:
                    f.write(response.text)
            else:
                print(
                    f"  FAILED to fetch stored MD from {api_md_url} (Status: {response.status_code})"
                )
        except Exception as e:
            print(f"  ERROR fetching stored MD: {e}")


if __name__ == "__main__":
    save_comparisons()
