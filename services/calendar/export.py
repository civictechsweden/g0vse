"""Publish calendar records alongside shared codes and source-path Markdown."""

import json
import os
from pathlib import Path

from services.calendar.fetcher import fetch_listing, refresh_details
from services.calendar.parser import CalendarError
from services.writer import Writer


def prepare_calendar_export(downloader, codes, files, root="data", *, force=False):
    root = Path(root)
    try:
        path = root / "api/kalendarium.json"
        previous = json.loads(path.read_text()) if path.exists() else []
        if not isinstance(previous, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("url"), str)
            for row in previous
        ):
            raise CalendarError("Invalid saved calendar records")
        records, labels = fetch_listing(downloader)
        labels = codes | labels
        records, markdown, failures, fetched = refresh_details(
            downloader,
            records,
            labels,
            {row["url"]: row for row in previous},
            root,
            force=force,
        )
        # Stage formatting before changing Markdown, codes or the JSON export plan.
        formatted = {
            url: Writer.format_md(content) for url, content in markdown.items()
        }
    except Exception as error:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else ""
        print(f"{prefix}Calendar refresh failed; keeping the previous export: {error}")
        return None
    for url, content in formatted.items():
        path = root / (url.strip("/") + ".md")
        if not path.exists() or path.read_text() != content:
            Writer.write_md(content, path)
    # Include labels discovered on both listing and detail pages.
    codes.update(labels)
    files["api/kalendarium.json"] = records
    print(f"Calendar: {len(records):,} events; {fetched:,} detail pages fetched.")
    if failures:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else ""
        print(
            f"{prefix}Calendar: {len(failures)} unavailable details; retaining saved details or listing-only records."
        )
        for url, error in failures[:5]:
            print(f"  {url}: {error}")
    return records
