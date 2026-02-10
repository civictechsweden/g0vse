import re

# from .new_chain_parser import extract_new_chains
# from .old_chain_parser import extract_old_chains
from .redirecter import get_final_url

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter

NEWLINES_RE = re.compile(r"\n{3,}")
MD_CONVERTER = MarkdownConverter(heading_style="ATX")


def get_document_list(response):
    message = response.get("Message")
    if not message:
        return None, None

    soup = BeautifulSoup(message, "html.parser")
    documents, codes = [], {}

    for block in soup.select("div.sortcompact"):
        try:
            a_tag = block.find("a")
            url = a_tag["href"]
            url = get_final_url(url) if url.endswith(".aspx") else url
            title = a_tag.get_text(strip=True)

            times = [t["datetime"] for t in block.select("time")]
            published, updated = (times + [None, None])[:2]

            ps = block.select("p")
            types = []
            senders = []
            is_sender = False

            for content in ps[-1].contents:
                if isinstance(content, str) and "från" in content:
                    is_sender = True
                elif getattr(content, "name", None) == "a":
                    code, name = extract_from_link(content)
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
                document["summary"] = ps[0].get_text(strip=True)

            documents.append(document)

        except Exception as e:
            print(e)
            print(soup)
            return None, None

    return documents, codes


def extract_from_link(link):
    return str(link["href"].split("/")[-1]), link.text


def extract_page(response):
    soup = BeautifulSoup(response, "html.parser")

    return extract_text(soup), extract_metadata(soup)


def extract_text(soup):
    if not soup:
        return None

    col_1 = soup.select_one(".col-1")
    title_el = soup.select_one("h1")
    if not col_1 or not title_el:
        return None

    title_text = title_el.find(string=True, recursive=False).strip()

    body = col_1.select("div.has-wordExplanation, div.cl")
    body = BeautifulSoup("".join(str(div) for div in body), "html.parser")

    markdown = MD_CONVERTER.convert_soup(body)
    markdown = NEWLINES_RE.sub("\n\n", markdown.strip()).replace("\\.", ".")

    return f"# {title_text}\n\n{markdown}\n"


def extract_metadata(soup):
    title_el = soup.select_one("h1")
    title_text = title_el.find(string=True, recursive=False).strip() if title_el else None

    journal_id = soup.select_one("span.h1-vignette")
    journal_id = journal_id.text if journal_id else None

    # if accordion_chain:
    #     accordion_chain = soup.select_one("#accordion--chain")
    #     chains = extract_old_chains(accordion_chain)
    # else:
    #     chains = extract_new_chains(soup)

    shortcuts = extract_shortcuts(soup)
    attachments = extract_attachments(soup)
    categories_raw = extract_categories(soup)
    
    categories = [c[0] for c in categories_raw]
    labels = {c[0]: c[1] for c in categories_raw}

    return {
        "title": title_text,
        "id": journal_id,
        # "chains": chains,
        "shortcuts": shortcuts,
        "attachments": attachments,
        "categories": categories,
        "labels": labels,
    }


def extract_shortcuts(soup):
    h2_old = soup.find("h2", string=lambda s: s and "Genväg" in s)
    shortcuts_old = [
        shortcut for shortcut in h2_old.find_parent("div").select("a")
    ] if h2_old else []

    h2_new = soup.find("h2", string=lambda s: s and "remitteras" in s)
    shortcuts_new = [
        shortcut for shortcut in h2_new.find_parent("div").select("a")
    ] if h2_new else []

    shortcuts = shortcuts_old + shortcuts_new

    return [{"name": shortcut.get_text(strip=True), "url": shortcut["href"]} for shortcut in shortcuts]


def extract_attachments(soup):
    links_new = soup.select("div.col-1 > .list--icons a")
    links_old = soup.select("div.col-1 > ul.list--Block--icons a")
    links = links_new + links_old
    return [{"name": link.get_text(strip=True), "url": link["href"]} for link in links]


def extract_categories(soup):
    div = soup.select_one(".block--politikomrLinks")

    if not div:
        return []

    return [extract_from_link(a) for a in div.select("a")]
