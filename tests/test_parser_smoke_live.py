import pytest

from services.chains.parser import extract_chains, memberships, normalize_url
from services.downloader import Downloader
from services.redirecter import get_final_url
from services.web_parser import extract_page

pytestmark = [pytest.mark.live, pytest.mark.smoke]

SOU_URL = "/rattsliga-dokument/statens-offentliga-utredningar/2026/02/sou-202612/"
PROPOSITION_URL = "/rattsliga-dokument/proposition/2019/11/prop.-20192038/"
EU_URL = "/kommenterade-dagordningar/2026/06/kommenterad-dagordning-radet-for-ekonomiska-och-finansiella-fragor-den-12-juni-2026/"


# These are old, immutable publications whose metadata and files should not
# disappear. Keep this list short: it runs before every scheduled data fetch.
STABLE_PAGES = [
    pytest.param(
        SOU_URL,
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


def fetch_chain(downloader, item_url, source_view_url=None):
    source_view_url = source_view_url or item_url
    html = downloader.get_webpage(source_view_url)
    assert html is not None, f"Could not fetch chain page {source_view_url}"
    observation, choices = extract_chains(
        html, item_url, source_view_url, resolve=get_final_url
    )
    assert observation["phases"], f"No chain found on {source_view_url}"
    assert observation["source"] == normalize_url(source_view_url, view=True)
    assert {
        doc["url"] for *_, doc in memberships(observation) if doc["current_page"]
    } == {item_url}, f"Current-page membership lost on {source_view_url}"
    return observation, choices


# Check known memberships, rather than exact counts: these chains can grow.
def test_current_swedish_chain_keeps_stages_and_continuation(downloader):
    observation, _ = fetch_chain(downloader, SOU_URL)
    actual = {
        (phase, actor, stage, doc["url"])
        for phase, actor, stage, doc in memberships(observation)
    }
    assert {
        (
            "Lagstiftning i Sverige",
            "Regeringen",
            "Kommittédirektiv",
            "/rattsliga-dokument/kommittedirektiv/2025/03/dir.-202533/",
        ),
        (
            "Lagstiftning i Sverige",
            "Regeringen",
            "Statens offentliga utredningar",
            SOU_URL,
        ),
        (
            "Lagstiftning i Sverige",
            "Regeringen",
            "Statens offentliga utredningar",
            "/rattsliga-dokument/statens-offentliga-utredningar/2025/09/sou-2025106/",
        ),
    } <= actual


def test_legacy_swedish_chain_keeps_external_statutes(downloader):
    observation, _ = fetch_chain(downloader, PROPOSITION_URL)
    actual = {(stage, doc["url"]) for _, _, stage, doc in memberships(observation)}
    assert {
        ("Proposition", PROPOSITION_URL),
        (
            "Svensk författningssamling",
            "https://svenskforfattningssamling.se/doc/202080.html",
        ),
        (
            "Svensk författningssamling",
            "https://svenskforfattningssamling.se/doc/202081.html",
        ),
    } <= actual


def test_eu_chain_keeps_selected_proposal_actors_and_alternate_views(downloader):
    observation, choices = fetch_chain(downloader, EU_URL, EU_URL + "?id=52025PC0989")
    assert observation["identity_celex"] == ["52025PC0989"]
    actual = {
        (phase, actor, doc["url"]) for phase, actor, _, doc in memberships(observation)
    }
    assert {
        (
            "Förslag till ny rättsakt inom EU",
            "EU-kommissionen",
            "https://eur-lex.europa.eu/legal-content/SV/ALL/?uri=CELEX:52025PC0989",
        ),
        (
            "Förslag till ny rättsakt inom EU",
            "Regeringen",
            "/faktapromemoria/2026/02/202526fpm61/",
        ),
        ("Förhandling och beslut inom EU", "Regeringen", EU_URL),
        (
            "Lagstiftning i Sverige",
            "Regeringen",
            "/rattsliga-dokument/proposition/2024/03/prop.-20232477/",
        ),
    } <= actual
    assert (
        normalize_url(EU_URL + "?id=52025PC0941;52025PC0942;52025PC0943", view=True)
        in choices
    )
