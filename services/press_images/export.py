"""Publish the portrait JSON and source-path Markdown after validating the listing."""

import json
import os
from pathlib import Path

from services.press_images.fetcher import fetch_listing, refresh_details
from services.press_images.parser import PressImageError
from services.writer import Writer


def prepare_press_image_export(downloader, codes, files, root="data"):
    root = Path(root)
    try:
        path = root / "api/pressbilder.json"
        previous = json.loads(path.read_text()) if path.exists() else []
        if not isinstance(previous, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("url"), str)
            for row in previous
        ):
            raise PressImageError("Invalid saved portrait records")
        records, labels = fetch_listing(downloader)
        labels = codes | labels
        records, markdown, failures = refresh_details(
            downloader, records, labels, {r["url"]: r for r in previous}, root
        )
        formatted = {
            url: Writer.format_md(content) for url, content in markdown.items()
        }
    except Exception as error:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else ""
        print(
            f"{prefix}Press-image refresh failed; keeping the previous export: {error}"
        )
        return None
    for url, content in formatted.items():
        path = root / (url.strip("/") + ".md")
        if not path.exists() or path.read_text() != content:
            Writer.write_md(content, path)
    codes.update(labels)
    files["api/pressbilder.json"] = records
    print(
        f"Press images: {len(records):,} portraits; {len({r['name'] for r in records}):,} distinct names."
    )
    if failures:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else ""
        print(
            f"{prefix}Press images: {len(failures)} unavailable details; retaining saved details or listing-only records."
        )
        for url, error in failures[:5]:
            print(f"  {url}: {error}")
    return records
