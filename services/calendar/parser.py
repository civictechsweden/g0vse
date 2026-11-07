"""Parse the CalendarEventPage list and its event detail pages."""

import re
from datetime import date
from urllib.parse import urlsplit

from html_to_markdown import convert
from selectolax.lexbor import LexborHTMLParser

from services.web_parser import CONVERSION_OPTIONS, extract_categories

ORIGIN = "https://www.regeringen.se"
LIST_FIELDS = ("url", "title", "start_date", "end_date", "participants", "summary")


class CalendarError(ValueError):
    pass


def text(node):
    return " ".join(node.text(separator=" ", strip=True).split()) if node else ""


def event_url(value):
    parsed = urlsplit(value or "")
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/kalendarium/")
        or ".." in parsed.path.split("/")
        or "\\" in parsed.path
    ):
        raise CalendarError(f"Invalid calendar URL: {value}")
    return parsed.path


def dates(nodes):
    values = [node.attributes.get("datetime") or "" for node in nodes]
    try:
        if len(values) not in {1, 2} or any(
            date.fromisoformat(value).isoformat() != value for value in values
        ):
            raise ValueError
    except ValueError as error:
        raise CalendarError("Invalid calendar event dates") from error
    if len(values) == 2 and values[1] < values[0]:
        raise CalendarError("Calendar event ends before it starts")
    # The listing sometimes repeats a single day as a start/end range.
    if len(values) == 2 and values[0] == values[1]:
        return values[:1]
    return values


def parse_fragment(response):
    if (
        not isinstance(response, dict)
        or type(response.get("TotalCount")) is not int
        or response["TotalCount"] < 0
        or not isinstance(response.get("Message"), str)
    ):
        raise CalendarError("Invalid calendar API response")
    tree = LexborHTMLParser(response["Message"])
    records, labels = [], {}
    for card in tree.css(".calendariumListItem"):
        scope = card.parent
        while scope is not None and not scope.css("time.timeCalSticker"):
            scope = scope.parent
        if scope is None:
            raise CalendarError("Calendar event has no dates")
        event_dates = dates(scope.css("time.timeCalSticker"))
        link, heading = card.css_first("a.readmore"), card.css_first("h2")
        if link is None or not text(heading):
            raise CalendarError("Calendar event has no title or link")
        participants = []
        for node in card.css("ul.list--icons a"):
            match = re.fullmatch(r"/tx/(\d+)/?", node.attributes.get("href") or "")
            if not match or not text(node):
                raise CalendarError("Invalid calendar participant")
            code = match[1]
            participants.append(code)
            labels[code] = text(node)
        row = {
            "url": event_url(link.attributes.get("href")),
            "title": text(heading),
            "start_date": event_dates[0],
            "participants": sorted(set(participants)),
        }
        if len(event_dates) == 2:
            row["end_date"] = event_dates[1]
        summary = text(card.css_first(".sortextended__excerpt"))
        if summary:
            row["summary"] = summary
        records.append(row)
    return response["TotalCount"], records, labels


def signature(record):
    return {key: record[key] for key in LIST_FIELDS if key in record}


def render_markdown(record, labels, html=None):
    date_text = record["start_date"]
    if record.get("end_date"):
        date_text += " – " + record["end_date"]
    if html is not None:
        tree = LexborHTMLParser(html)
        body = tree.css_first("main.calendarevent .col-1")
        if body is None:
            raise CalendarError("Missing calendar body")
        for node in body.css("h1, .timeCalSticker--span-wrap, #readspeaker"):
            node.decompose()
        for node in body.css("a[href^='/']"):
            node.attrs["href"] = ORIGIN + (node.attributes.get("href") or "")
        result = convert(body.html or "", CONVERSION_OPTIONS)
        content = result if isinstance(result, str) else result.content or ""
    else:
        content = record.get("summary", "") + "\n\n"
        if record["participants"]:
            content += "## Deltagare\n\n" + "\n".join(
                f"* [{labels.get(code, code)}]({ORIGIN}/tx/{code})"
                for code in record["participants"]
            )
        if record.get("location"):
            content += "\n\nPlats: " + record["location"]
    return f"# {record['title']}\n\nDatum: {date_text}\n\n{content}\n"


def parse_detail(html, record):
    tree = LexborHTMLParser(html)
    identifier = tree.css_first('meta[name="DC.Identifier"]')
    if identifier is not None and urlsplit(
        identifier.attributes.get("content") or ""
    ).path.rstrip("/") != record["url"].rstrip("/"):
        raise CalendarError("Calendar detail URL disagrees with its listing")
    body = tree.css_first("main.calendarevent .col-1")
    if body is None or text(body.css_first("h1")) != record["title"]:
        raise CalendarError("Calendar detail page does not match its listing")
    event_dates = dates(body.css("time.timeCalSticker"))
    if event_dates != [record["start_date"]] + (
        [record["end_date"]] if record.get("end_date") else []
    ):
        raise CalendarError("Calendar detail dates disagree with the listing")
    details, labels = {}, dict(extract_categories(tree))
    if labels:
        details["categories"] = sorted(labels)
    for key, selector in [
        ("published", 'meta[name="DC.Date.Created"]'),
        ("updated", 'meta[name="DC.Date.Modified"]'),
    ]:
        node = tree.css_first(selector)
        if key == "published":
            node = tree.css_first('meta[name="published"]') or node
        if node is not None:
            try:
                details[key] = date.fromisoformat(
                    (node.attributes.get("content") or "")[:10]
                ).isoformat()
            except (KeyError, ValueError) as error:
                raise CalendarError("Invalid calendar publication metadata") from error
    if details.get("updated") == details.get("published"):
        details.pop("updated", None)
    for node in body.css(".block--time-time p"):
        match = re.match(r"Plats:\s*(.+)", text(node))
        if match:
            details["location"] = match[1]
    return details, labels, render_markdown(record, labels, html)
