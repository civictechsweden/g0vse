import re

from .new_chain_parser import extract_new_chains
from .old_chain_parser import extract_old_chains
from .redirecter import get_final_url

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter


class WebParser(object):
    @staticmethod
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
                        code, name = WebParser.extract_from_link(content)
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

    @staticmethod
    def extract_from_link(link):
        return int(link["href"].split("/")[-1]), link.text

    @staticmethod
    def extract_page(response):
        soup = BeautifulSoup(response, "html.parser")

        return WebParser.extract_text(soup), WebParser.extract_metadata(soup)

    @staticmethod
    def extract_text(soup):
        col_1 = soup.select_one(".col-1")
        title = soup.select_one("h1").find(text=True).strip()

        body = col_1.select(
            "div.has-wordExplanation, div.cl, p.has-wordExplanation, p.cl"
        )
        body = BeautifulSoup("".join(str(div) for div in body), "html.parser")

        markdown_text = MarkdownConverter(heading_style="ATX").convert_soup(body)
        markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text.strip())

        return f"# {title}\n\n{markdown_text}\n"

    @staticmethod
    def extract_metadata(soup):
        journal_id = soup.select_one("span.h1-vignette")
        journal_id = journal_id.text if journal_id else None

        accordion_chain = soup.select_one("#accordion--chain")

        if accordion_chain:
            chains = extract_old_chains(accordion_chain)
        else:
            chains = extract_new_chains(soup)

        shortcuts = WebParser.extract_shortcuts(soup)
        attachments = WebParser.extract_attachments(soup)
        categories = WebParser.extract_categories(soup)

        return {
            "id": journal_id,
            "chains": chains,
            "shortcuts": shortcuts,
            "attachments": attachments,
            "categories": categories,
        }

    @staticmethod
    def extract_shortcuts(soup):
        h2 = soup.find("h2", text="Genvägar")

        if h2:
            return [
                {"name": a.text, "url": a["href"]}
                for a in h2.find_parent("div").find_all("a")
            ]

        return []

    @staticmethod
    def extract_attachments(soup):
        links = soup.find_all(
            "a",
            href=lambda href: href
            and (
                href.startswith("/contentassets/") or href.startswith("/globalassets/")
            ),
        )

        return [{"name": link.text, "url": link["href"]} for link in links]

    @staticmethod
    def extract_categories(soup):
        div = soup.select_one(".block--politikomrLinks")

        if not div:
            return []

        return [WebParser.extract_from_link(a) for a in div.select("a")]
