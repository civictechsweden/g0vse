import pytest

from services.downloader import Downloader
from services.press_images.fetcher import fetch_listing
from services.press_images.parser import parse_detail

pytestmark = [pytest.mark.live, pytest.mark.smoke]


def test_live_portrait_listing_and_one_detail_keep_image_metadata():
    downloader = Downloader()
    try:
        records, labels = fetch_listing(downloader)
        assert records and labels
        assert len({r["url"] for r in records}) == len(records)
        row = records[0]
        html = downloader.get_webpage(row["url"])
        assert html
        details, _, markdown = parse_detail(html, row)
        assert details["image"].startswith("https://www.regeringen.se/")
        assert details["image"] in markdown
        assert row["name"] in markdown
        if details.get("credit"):
            assert details["credit"] in markdown
    finally:
        downloader.b.close()
