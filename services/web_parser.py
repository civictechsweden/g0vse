import re

# from .new_chain_parser import extract_new_chains
# from .old_chain_parser import extract_old_chains
from .redirecter import get_final_url

from selectolax.parser import HTMLParser
from html_to_markdown import convert, ConversionOptions

NEWLINES_RE = re.compile(r"\n{3,}")
CONVERSION_OPTIONS = ConversionOptions(heading_style="atx", bullets="*")


def get_document_list(response):
    message = response.get("Message")
    if not message:
        return None, None

    tree = HTMLParser(message)
    documents, codes = [], {}

    for block in tree.css("div.sortcompact"):
        try:
            a_tag = block.css_first("a")
            if not a_tag:
                continue

            url = a_tag.attributes.get("href")
            url = get_final_url(url) if url.endswith(".aspx") else url
            title = a_tag.text(strip=True)

            times = [t.attributes.get("datetime") for t in block.css("time")]
            published, updated = (times + [None, None])[:2]

            ps = block.css("p")
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


def extract_page(response):
    tree = HTMLParser(response)
    return extract_text(tree), extract_metadata(tree)


def extract_text(tree):
    if not tree:
        return None

    col_1 = tree.css_first(".col-1")
    title_el = tree.css_first("h1")
    if not col_1 or not title_el:
        return None

    # Extract clean title (direct text of h1, ignoring vignette span)
    title_text = ""
    for node in title_el.iter(include_text=True):
        if node.tag == "-text":
            title_text += node.text()
    title_text = title_text.strip()

    # For markdown conversion, we grab the HTML of the body divs and feed it to html-to-markdown
    # We select summary first to ensure it appears at the top
    body_nodes = col_1.css("div.cl, div.has-wordExplanation")
    body_html = "".join(node.html for node in body_nodes)

    markdown = convert(body_html, CONVERSION_OPTIONS)
    markdown = NEWLINES_RE.sub("\n\n", markdown.strip()).replace("\\.", ".")

    return f"# {title_text}\n\n{markdown}\n"


def extract_metadata(tree):
    # Extract ID first before potentially modifying anything (though we won't modify the tree here)
    journal_id_el = tree.css_first("span.h1-vignette")
    journal_id = journal_id_el.text(strip=True) if journal_id_el else None

    # Extract Title
    title_el = tree.css_first("h1")
    title_text = None
    if title_el:
        # Same logic as extract_text to get clean title
        txt = ""
        for node in title_el.iter(include_text=True):
            if node.tag == "-text":
                txt += node.text()
        title_text = txt.strip()

    shortcuts = extract_shortcuts(tree)
    attachments = extract_attachments(tree)
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


def extract_shortcuts(tree):
    shortcuts = []
    seen_urls = set()

    col_2 = tree.css_first(".col-2")
    if col_2:
        for a in col_2.css("a"):
            url = a.attributes.get("href")
            if url and url not in seen_urls:
                shortcuts.append({"name": a.text(strip=True), "url": url})
                seen_urls.add(url)

    return shortcuts


def extract_attachments(tree):
    # div.col-1 > .list--icons a  OR  div.col-1 > ul.list--Block--icons a
    links = []

    # CSS selector can handle multiple comma-separated paths
    selector = "div.col-1 > .list--icons a, div.col-1 > ul.list--Block--icons a"
    for a in tree.css(selector):
        links.append({"name": a.text(strip=True), "url": a.attributes.get("href")})

    return links


def extract_categories(tree):
    div = tree.css_first(".block--politikomrLinks")
    if not div:
        return []

    cats = []
    for a in div.css("a"):
        href = a.attributes.get("href", "")
        code = href.split("/")[-1]
        name = a.text(strip=True)
        cats.append((str(code), name))

    return cats
