import re

# from .new_chain_parser import extract_new_chains
# from .old_chain_parser import extract_old_chains
from .redirecter import get_final_url

from selectolax.parser import HTMLParser
from html_to_markdown import convert, ConversionOptions

NEWLINES_RE = re.compile(r"\n{3,}")
CONVERSION_OPTIONS = ConversionOptions(heading_style="atx", bullets="*")

# Selectors
SORT_COMPACT_SELECTOR = "div.sortcompact"
A_TAG_SELECTOR = "a"
TIME_SELECTOR = "time"
P_TAG_SELECTOR = "p"
COL_1_SELECTOR = ".col-1"
COL_2_SELECTOR = ".col-2"
H1_SELECTOR = "h1"
BODY_CONTENT_SELECTOR = "div.cl, div.has-wordExplanation"
H1_VIGNETTE_SELECTOR = "span.h1-vignette"
ATTACHMENTS_SELECTOR = "div.col-1 > .list--icons a, div.col-1 > ul.list--Block--icons a"
POLITIK_LINKS_SELECTOR = ".block--politikomrLinks"

# Common links to exclude from shortcuts and attachments
EXCLUDED_URLS = {
    "/",
    "/prenumerera-via-e-post/",
    "/rapporter/2021/09/svara-pa-remiss/",
    "/sa-styrs-sverige/lagstiftningsprocessen/",
    "https://twitter.com/socialdep",
    "https://www.youtube.com/channel/UCTCf9DNzLC78u2o_4Iu2frw",
    "https://twitter.com/ForsvarsdepSv",
    "https://www.linkedin.com/company/forsvarsdepartementet-se",
    "/press/information-om-regeringens-presstraffar/",
    "/sveriges-regering/finansdepartementet/statens-budget/",
    "/sverige-i-eu/",
    "http://www.ohchr.org/en/hrbodies/cat/pages/catindex.aspx",
    "/regeringsarenden/",
    "https://newsroom.consilium.europa.eu/",
    "https://www.consilium.europa.eu/sv/",
    "/uds-reseinformation/avradan---nar-ud-avrader-fran-resor/vad-innebar-avradan--fragor-och-svar/",
    "/ud-avrader/",
    "http://eur-lex.europa.eu/legal-content/SV/TXT/?uri=celex:32016R0679",
    "https://twitter.com/arbetsmarkdep",
    "/sa-styrs-sverige/regeringens-arbete-pa-eu-niva/",
    "http://eu.riksdagen.se/",
    "/sverige-i-eu/sveriges-arbete-i-ministerradet/",
    "/rattsliga-dokument/lagradsremiss/",
    "https://www.statskontoret.se/statsliggaren/",
}


def get_document_list(response):
    message = response.get("Message")
    if not message:
        return None, None

    tree = HTMLParser(message)
    documents, codes = [], {}

    for block in tree.css(SORT_COMPACT_SELECTOR):
        try:
            a_tag = block.css_first(A_TAG_SELECTOR)
            if not a_tag:
                continue

            url = a_tag.attributes.get("href")
            url = get_final_url(url) if url.endswith(".aspx") else url
            title = a_tag.text(strip=True)

            times = [t.attributes.get("datetime") for t in block.css(TIME_SELECTOR)]
            published, updated = (times + [None, None])[:2]

            ps = block.css(P_TAG_SELECTOR)
            if not ps:
                continue

            types = []
            senders = []
            is_sender = False

            # The last <p> contains types and senders
            last_p = ps[-1]
            for node in last_p.iter(include_text=True):
                if node.tag == "-text":
                    if "från" in node.text():
                        is_sender = True
                elif node.tag == "a":
                    code, name = extract_from_link(node)
                    codes.setdefault(code, name)
                    (senders if is_sender else types).append(code)

            document = {
                "title": title,
                "url": url,
                "published": published,
                "updated": updated,
                "types": types,
                "senders": senders,
            }

            if len(ps) > 1:
                document["summary"] = ps[0].text(strip=True)

            documents.append(document)

        except Exception as e:
            print(f"Error parsing block: {e}")
            return None, None

    return documents, codes


def extract_from_link(link):
    href = link.attributes.get("href", "")
    return str(href.split("/")[-1]), link.text(strip=True)


def extract_page(response, item_url=None):
    tree = HTMLParser(response)
    return extract_text(tree), extract_metadata(tree, item_url)


def extract_text(tree):
    if not tree:
        return None

    col_1 = tree.css_first(COL_1_SELECTOR)
    title_el = tree.css_first(H1_SELECTOR)
    if not col_1 or not title_el:
        return None

    # Extract clean title (direct text of h1, ignoring vignette span)
    title_text = "".join(
        node.text() for node in title_el.iter(include_text=True) if node.tag == "-text"
    ).strip()

    # For markdown conversion, we grab the HTML of the body divs and feed it to html-to-markdown
    # We select summary first to ensure it appears at the top
    body_nodes = col_1.css(BODY_CONTENT_SELECTOR)
    body_html = "".join(node.html for node in body_nodes)

    markdown = convert(body_html, CONVERSION_OPTIONS)
    markdown = NEWLINES_RE.sub("\n\n", markdown.strip()).replace("\\.", ".")

    return f"# {title_text}\n\n{markdown}\n"


def extract_metadata(tree, item_url=None):
    # Extract ID first before potentially modifying anything (though we won't modify the tree here)
    journal_id_el = tree.css_first(H1_VIGNETTE_SELECTOR)
    journal_id = journal_id_el.text(strip=True) if journal_id_el else None

    # Extract Title
    title_el = tree.css_first(H1_SELECTOR)
    title_text = None
    if title_el:
        # Same logic as extract_text to get clean title
        title_text = "".join(
            node.text()
            for node in title_el.iter(include_text=True)
            if node.tag == "-text"
        ).strip()

    shortcuts = extract_shortcuts(tree, item_url)
    attachments = extract_attachments(tree, item_url)
    categories_raw = extract_categories(tree)

    categories = [c[0] for c in categories_raw]
    labels = {c[0]: c[1] for c in categories_raw}

    return {
        "title": title_text,
        "id": journal_id,
        "shortcuts": shortcuts,
        "attachments": attachments,
        "categories": categories,
        "labels": labels,
    }


def extract_shortcuts(tree, item_url=None):
    shortcuts = []
    seen_urls = set()
    if item_url:
        seen_urls.add(item_url)

    col_2 = tree.css_first(COL_2_SELECTOR)
    if col_2:
        for a in col_2.css(A_TAG_SELECTOR):
            url = a.attributes.get("href")
            if url and url not in EXCLUDED_URLS and url not in seen_urls:
                shortcuts.append({"name": a.text(strip=True), "url": url})
                seen_urls.add(url)

    return shortcuts


def extract_attachments(tree, item_url=None):
    # div.col-1 > .list--icons a  OR  div.col-1 > ul.list--Block--icons a
    links = []

    # CSS selector can handle multiple comma-separated paths
    for a in tree.css(ATTACHMENTS_SELECTOR):
        url = a.attributes.get("href")
        if url:
            links.append({"name": a.text(strip=True), "url": url})

    return links


def extract_categories(tree):
    div = tree.css_first(POLITIK_LINKS_SELECTOR)
    if not div:
        return []

    cats = []
    for a in div.css(A_TAG_SELECTOR):
        href = a.attributes.get("href", "")
        code = href.split("/")[-1]
        name = a.text(strip=True)
        cats.append((str(code), name))

    return cats
