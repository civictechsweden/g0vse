import pytest

from services.calendar.fetcher import query_url
from services.calendar.parser import parse_detail, parse_fragment
from services.downloader import Downloader

pytestmark = [pytest.mark.live, pytest.mark.smoke]


def test_live_calendar_pages_and_detail_keep_dates_and_body():
    downloader = Downloader()
    try:
        total, first, _ = parse_fragment(downloader.b.get_json(query_url(1, 2)))
        next_total, second, _ = parse_fragment(downloader.b.get_json(query_url(2, 2)))
        assert total == next_total and total >= 4
        assert len(first) == len(second) == 2
        assert not {r["url"] for r in first} & {r["url"] for r in second}
        html = downloader.get_webpage(first[0]["url"])
        assert html
        details, _, markdown = parse_detail(html, first[0])
        assert details.get("published")
        assert first[0]["start_date"] in markdown and first[0]["title"] in markdown
    finally:
        downloader.b.close()
