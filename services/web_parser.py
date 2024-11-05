import re

from .new_chain_parser import extract_new_chains
from .old_chain_parser import extract_old_chains
from .redirecter import get_final_url

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


def get_document_list(response):
    documents = []

    if "Message" not in response:
        return None, None

    soup = BeautifulSoup(response["Message"], "html.parser")
    blocks = soup.select("div.sortcompact")
    codes = {}

    for block in blocks:
        try:
            url = block.find("a")["href"]
            url = get_final_url(url) if ".aspx" in url else url

            title = block.find("a").text
            dates = [t["datetime"] for t in block.select("time")]
            published = dates[0] if dates else None
            updated = dates[1] if len(dates) > 1 else None

            ps = block.select("p")
            is_sender = False
            types = []
            senders = []

            for content in ps[-1].contents:
                if isinstance(content, str) and "från" in content:
                    is_sender = True
                elif content.name == "a":
                    code, name = extract_from_link(content)
                    codes[code] = name

                    if is_sender:
                        senders.append(code)
                    else:
                        types.append(code)

            document = {
                "title": title,
                "url": url,
                "published": published,
                "updated": updated,
                "types": types,
                "senders": senders,
            }

            if len(ps) > 1:
                document["summary"] = ps[0].text.strip()

            documents.append(document)
        except Exception as e:
            print(e)
            print(soup)
            return None, None

    return documents, codes


def extract_from_link(link):
    return str(link["href"].split("/")[-1]), link.text


def is_attachment(url):
    return url.startswith("/contentassets/") or url.startswith("/globalassets/")


def extract_page(response):
    soup = BeautifulSoup(response, "html.parser")

    return extract_text(soup), extract_metadata(soup)


def extract_text(soup):

    if not soup:
        return None
    
    col_1 = soup.select_one(".col-1")
    title = soup.select_one("h1").find(text=True).strip()

    if not col_1:
        return None
    
    body = col_1.select("div.has-wordExplanation, div.cl")
    body = BeautifulSoup("".join(str(div) for div in body), "html.parser")

    markdown_text = MarkdownConverter(heading_style="ATX").convert_soup(body)
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text.strip())

    return f"# {title}\n\n{markdown_text}\n"


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
    h2 = soup.find("h2", text="Genvägar")

    if h2:
        return [
            {"name": a.text, "url": a["href"]}
            for a in h2.find_parent("div").find_all("a")
            if not is_attachment(a["href"])
        ]

    return []


def extract_attachments(soup):
    links = soup.find_all("a", href=lambda href: href and is_attachment(href))

    return [{"name": link.text, "url": link["href"]} for link in links]


def extract_categories(soup):
    div = soup.select_one(".block--politikomrLinks")

    if not div:
        return []

    return [extract_from_link(a) for a in div.select("a")]
