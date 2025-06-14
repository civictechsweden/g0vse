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
    title = soup.select_one("h1")
    if not col_1 or not title:
        return None

    body = col_1.select("div.has-wordExplanation, div.cl")
    body = BeautifulSoup("".join(str(div) for div in body), "html.parser")

    markdown = MD_CONVERTER.convert_soup(body)
    markdown = NEWLINES_RE.sub("\n\n", markdown.strip()).replace("\\.", ".")

    return f"# {title.get_text(strip=True)}\n\n{markdown}\n"


def extract_metadata(soup):
    journal_id = soup.select_one("span.h1-vignette")
    journal_id = journal_id.text if journal_id else None

    # if accordion_chain:
    #     accordion_chain = soup.select_one("#accordion--chain")
    #     chains = extract_old_chains(accordion_chain)
    # else:
    #     chains = extract_new_chains(soup)

    shortcuts = extract_shortcuts(soup)
    attachments = extract_attachments(soup)
    categories = extract_categories(soup)

    return {
        "id": journal_id,
        # "chains": chains,
        "shortcuts": shortcuts,
        "attachments": attachments,
        "categories": categories,
    }


def extract_shortcuts(soup):
    h2 = soup.find("h2", string=lambda s: s and "Genväg" in s)

    return (
        [
            {"name": a.get_text(strip=True), "url": a["href"]}
            for a in h2.find_parent("div").select("a")
        ]
        if h2
        else []
    )


def extract_attachments(soup):
    links = soup.select("div.col-1 ul.list--Block--icons a")
    return [{"name": link.get_text(strip=True), "url": link["href"]} for link in links]


def extract_categories(soup):
    div = soup.select_one(".block--politikomrLinks")

    if not div:
        return []

    return [extract_from_link(a) for a in div.select("a")]
