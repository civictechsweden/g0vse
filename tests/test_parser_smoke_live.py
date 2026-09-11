import pytest

from services.downloader import Downloader
from services.web_parser import extract_page


# These are old, immutable publications whose metadata and files should not
# disappear. Keep this list short: it runs before every scheduled data fetch.
STABLE_PAGES = [
    pytest.param(
        "/rattsliga-dokument/statens-offentliga-utredningar/2026/02/sou-202612/",
        "Om överföring av Sjätte AP-fondens verksamhet och tillgångar till Andra AP-fonden",
        "SOU 2026:12",
        "/contentassets/c8f3c1b7d72e4728bb5033f5c328e1f2/om-overforing-av-sjatte-ap-fondens-verksamhet-och-tillgangar-till-andra-ap-fonden-sou-202612.pdf",
        id="sou",
    ),
    pytest.param(
        "/rattsliga-dokument/kommittedirektiv/2025/11/dir.-2025104",
        "Tilläggsdirektiv till delegationen för migrationsstudier (Ju 2013:17)",
        "Dir. 2025:104",
        "/contentassets/62afbc9e00ef42e5b93b0ae9f2e7a349/tillaggsdirektiv-delegation-for-migrationsstudier-ju-2013_17.pdf",
        id="committee-directive",
    ),
    pytest.param(
        "/rapporter/2025/01/konsfordelningen-ar-fortsatt-jamn-i-statliga-myndigheters-styrelser-och-insynsrad/",
        "Könsfördelningen är fortsatt jämn i statliga myndigheters styrelser och insynsråd",
        "Diarienummer: A2025/00005",
        "/contentassets/10ba9dcb84f4474bb0229e1e8075dade/konsfordelningen-i-statliga-myndigheters-styrelser-och-insynsrad-m.m-2023.pdf",
        id="report",
    ),
]


@pytest.fixture(scope="module")
def downloader():
    instance = Downloader()
    yield instance
    instance.b.close()


@pytest.mark.parametrize("url,title,journal_id,attachment_url", STABLE_PAGES)
def test_stable_page_keeps_essential_metadata(
    downloader, url, title, journal_id, attachment_url
):
    html = downloader.get_webpage(url)

    assert html is not None, f"Could not fetch stable page {url}"
    markdown, metadata = extract_page(html, url)

    assert markdown and markdown.startswith(f"# {title}\n")
    assert metadata["title"] == title
    assert metadata["id"] == journal_id
    assert attachment_url in {
        attachment["url"] for attachment in metadata["attachments"]
    }
