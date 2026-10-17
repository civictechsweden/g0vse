"""Parse the modern CasePage listing and weekly agenda layout without guessing IDs."""

import re
from datetime import date
from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser, LexborNode

ORIGIN = "https://www.regeringen.se"
LISTING = "/regeringsarenden/"
RESULT_SELECTOR = ".sortcompact.sortextended"
WEEK = re.compile(r"vecka\s+(\d{1,2})\s*,?\s*(\d{4})", re.IGNORECASE)
MONTHS: tuple[str, ...] = (
    "januari",
    "februari",
    "mars",
    "april",
    "maj",
    "juni",
    "juli",
    "augusti",
    "september",
    "oktober",
    "november",
    "december",
)
DAY = re.compile(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?", re.I)


class AgendaError(ValueError):
    """The listing could not be retrieved or parsed completely."""


def clean(text: str) -> str:
    return " ".join(text.replace("\u00ad", "").split())


def text(node: LexborNode | None) -> str:
    return clean(node.text(separator=" ", strip=True)) if node else ""


def title_text(node: LexborNode) -> str:
    # Only explicit HTML line breaks are semantic; indentation is not a new line.
    tree = LexborHTMLParser(node.html or "")
    for br in tree.css("br"):
        br.replace_with("\ue000")
    return "\n".join(
        clean(line) for line in tree.text(separator="").split("\ue000") if clean(line)
    )


def weekly_url(href: str) -> str:
    parts = urlsplit(urljoin(ORIGIN, href))
    if (
        parts.hostname not in {"www.regeringen.se", "regeringen.se"}
        or not parts.path.startswith(LISTING)
        or parts.path.rstrip("/") == LISTING.rstrip("/")
    ):
        raise AgendaError(f"Unexpected weekly source: {href}")
    return parts.path.rstrip("/") + "/"


def week_info(title: str) -> tuple[int, int]:
    match = WEEK.search(clean(title))
    if not match or not 1 <= int(match[1]) <= 53:
        raise AgendaError(f"Missing year/week in weekly title: {title}")
    return int(match[2]), int(match[1])


def category_labels(tree: LexborHTMLParser) -> dict[str, str]:
    labels = {}
    for node in tree.css("input[data-cid][title]"):
        code, name = node.attributes["data-cid"], node.attributes["title"]
        if code and name:
            labels[code] = clean(name)
    return labels


def listing_root(html: str) -> tuple[str, dict[str, str]]:
    tree = LexborHTMLParser(html)
    roots = tree.css('[data-filterbytype="CasePage"][data-rootpage]')
    root = (roots[0].attributes["data-rootpage"] or "") if len(roots) == 1 else ""
    if not root.isdigit():
        raise AgendaError("Missing or ambiguous CasePage listing root")
    return root, category_labels(tree)


def entry_fields(node: LexborNode) -> dict:
    values = dict(
        re.findall(
            r"(?:^|·)\s*(Regeringsärendenummer|Diarienummer|Ansvarig chefstjänsteman):\s*([^·]*)",
            text(node),
        )
    )
    number = clean(values.get("Regeringsärendenummer", ""))
    if not {"Regeringsärendenummer", "Ansvarig chefstjänsteman"} <= values.keys():
        raise AgendaError(f"Incomplete agenda entry fields: {text(node)}")
    return {
        "agenda_number": number or None,
        "journal_ids": [
            clean(value)
            for value in re.split(r"[,;]", values.get("Diarienummer", ""))
            if clean(value)
        ],
        "responsible_official": clean(values["Ansvarig chefstjänsteman"]) or None,
    }


def parse_fragment(response: dict) -> tuple[int, list[dict]]:
    total, html = response.get("TotalCount"), response.get("Message")
    if type(total) is not int or total < 0 or not isinstance(html, str):
        raise AgendaError("Invalid CasePage response: expected TotalCount and Message")
    tree = LexborHTMLParser(html)
    records = []
    for block in tree.css(RESULT_SELECTOR):
        title = block.css_first("p.sortextended__excerpt strong")
        paragraphs = block.css("p.sortextended__excerpt")
        footer = block.css_first(".block--timeLinks")
        link = footer.css_first("a[href]") if footer else None
        if title is None or len(paragraphs) != 2 or link is None:
            raise AgendaError("Incomplete CasePage result fragment")
        source = weekly_url(link.attributes["href"] or "")
        year, week = week_info(text(link))
        context = text(footer).rsplit("·", 1)[-1].strip()
        if "," in context:
            minister, department = (clean(v) for v in context.rsplit(",", 1))
        else:
            minister, department = "", context
        if not department or not title_text(title):
            raise AgendaError(f"Missing title or department on {source}")
        records.append(
            {
                "source": source,
                "year": year,
                "week": week,
                "department": department,
                "minister": minister or None,
                "title": title_text(title),
                **entry_fields(paragraphs[1]),
            }
        )
    return total, records


def heading_date(heading: str, year: int, week: int) -> str | None:
    match = DAY.search(heading)
    if not match:
        return None
    month, day = MONTHS.index(match[2].lower()) + 1, int(match[1])
    years = [int(match[3])] if match[3] else [year - 1, year, year + 1]
    candidates = []
    for calendar_year in years:
        try:
            candidate = date(calendar_year, month, day)
        except ValueError:
            continue
        if match[3] or candidate.isocalendar()[:2] == (year, week):
            candidates.append(candidate.isoformat())
    return candidates[0] if len(candidates) == 1 else None


def weekly_context(
    html: str, source: str, year: int, week: int
) -> tuple[list[dict], dict[str, str]]:
    """Read dates from actual headings; a vanished source cannot supply a date."""
    tree = LexborHTMLParser(html)
    try:
        if week_info(text(tree.css_first("h1"))) != (year, week):
            return [], {}
    except AgendaError:
        return [], {}
    records = []
    meeting_date = None
    for node in tree.css(".col-1 > h2, .col-1 > .c-faq__accordion"):
        if node.tag == "h2":
            meeting_date = heading_date(text(node), year, week)
            continue
        department = text(node.css_first("h3"))
        for section in node.css("section.case"):
            minister = text(section.css_first("h4 strong")) or None
            for title in section.css("article.sortextended h5"):
                details = (
                    title.parent.css_first("p.sortextended__excerpt")
                    if title.parent
                    else None
                )
                if details is None:
                    raise AgendaError(f"Missing weekly entry fields on {source}")
                records.append(
                    {
                        "source": source,
                        "year": year,
                        "week": week,
                        "department": department,
                        "minister": minister,
                        "title": title_text(title),
                        **entry_fields(details),
                        "meeting_date": meeting_date,
                    }
                )
    return records, category_labels(tree)
