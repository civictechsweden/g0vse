"""Parse the public press portrait listing and image detail pages."""

from datetime import date
from urllib.parse import urljoin, urlsplit

from html_to_markdown import convert
from selectolax.lexbor import LexborHTMLParser

from services.web_parser import CONVERSION_OPTIONS, extract_categories

ORIGIN = "https://www.regeringen.se"
LISTING = "/pressbilder/"


class PressImageError(ValueError):
    pass


def text(node):
    return " ".join(node.text(separator=" ", strip=True).split()) if node else ""


def portrait_url(value):
    parsed = urlsplit(value or "")
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith(LISTING)
        or ".." in parsed.path.split("/")
        or "\\" in parsed.path
    ):
        raise PressImageError(f"Invalid portrait URL: {value}")
    return parsed.path


def image_url(value):
    if not value:
        raise PressImageError("Missing image URL")
    url = urljoin(ORIGIN, value)
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"regeringen.se", "www.regeringen.se"}
        or parsed.username
        or parsed.password
        or parsed.port
    ):
        raise PressImageError("Unexpected image origin")
    return url


def listing_root(html):
    tree = LexborHTMLParser(html)
    roots = {
        node.attributes.get("data-rootpage")
        for node in tree.css('[data-filterbytype="PressImagePage"][data-rootpage]')
    }
    if len(roots) != 1:
        raise PressImageError("Missing or ambiguous press-image root")
    root = roots.pop()
    if not root or not root.isdigit():
        raise PressImageError("Invalid press-image root")
    labels = {
        node.attributes["data-cid"]: node.attributes["title"]
        for node in tree.css("input[data-cid][title]")
        if node.attributes.get("data-cid") and node.attributes.get("title")
    }
    return root, labels


def parse_fragment(response):
    if (
        not isinstance(response, dict)
        or type(response.get("TotalCount")) is not int
        or response["TotalCount"] <= 0
        or not isinstance(response.get("Message"), str)
    ):
        raise PressImageError("Invalid press-image API response")
    tree = LexborHTMLParser(response["Message"])
    if tree.root is None:
        raise PressImageError("Empty press-image fragment")
    rows, seen, department = [], set(), None
    for node in tree.root.traverse():
        classes = node.attributes.get("class", "") or ""
        if node.tag == "h2" and "press__department-header" in classes.split():
            department = text(node)
        if node.tag != "div" or "notis--alpha" not in classes.split():
            continue
        heading = node.css_first("h3")
        link, image = node.css_first(".list--icons a"), node.css_first("img")
        if not department or not text(heading) or link is None or image is None:
            raise PressImageError("Incomplete press-image card")
        url = portrait_url(link.attributes.get("href"))
        if url in seen:
            raise PressImageError(f"Repeated portrait URL: {url}")
        seen.add(url)
        row = {
            "url": url,
            "name": text(heading),
            "department": department,
            "thumbnail": image_url(image.attributes.get("src")),
        }
        if role := text(node.css_first("p")):
            row["role"] = role
        if alt := image.attributes.get("alt"):
            row["alt"] = alt
        rows.append(row)
    if len(rows) != response["TotalCount"]:
        raise PressImageError("Incomplete press-image listing")
    return sorted(rows, key=lambda r: (r["department"], r["name"], r["url"]))


def render_markdown(record, html=None):
    if html is not None:
        tree = LexborHTMLParser(html)
        body = tree.css_first("main .col-1")
        if body is None:
            raise PressImageError("Missing portrait body")
        for node in body.css("img[src]"):
            node.attrs["src"] = image_url(node.attributes.get("src"))
        for node in body.css("a[href^='/']"):
            node.attrs["href"] = ORIGIN + (node.attributes.get("href") or "")
        result = convert(body.html or "", CONVERSION_OPTIONS)
        content = result if isinstance(result, str) else result.content or ""
    else:
        content = f"{record.get('role', '')}\n\n![{record.get('alt', record['name'])}]({record['thumbnail']})"
        for key in ("caption", "credit"):
            if record.get(key):
                content += "\n\n" + record[key]
        if record.get("image"):
            content += f"\n\n[Ladda ner bilden i högupplöst format]({record['image']})"
        if record.get("rights"):
            content += "\n\n## Upphovsrätt\n\n" + record["rights"]
    return f"# {record['name']}\n\n{record['department']}\n\n{content}\n"


def parse_detail(html, record):
    tree = LexborHTMLParser(html)
    identifier = tree.css_first('meta[name="DC.Identifier"]')
    if identifier is not None and urlsplit(
        identifier.attributes.get("content") or ""
    ).path.rstrip("/") != record["url"].rstrip("/"):
        raise PressImageError("Portrait detail URL disagrees with its listing")
    body = tree.css_first("main .col-1")
    if (
        body is None
        or text(tree.css_first("main h1")) != record["name"]
        or body.css_first("figure.press-img-container") is None
    ):
        raise PressImageError("Portrait detail page does not match its listing")
    download = body.css_first("a.readmore--download")
    if download is None:
        raise PressImageError("Portrait detail page has no original image link")
    details = {"image": image_url(download.attributes.get("href"))}
    for key, selector in [
        ("caption", ".figcaption__text"),
        ("credit", ".figcaption__photocred"),
    ]:
        if value := text(body.css_first(selector)):
            details[key] = value
    for island in body.css(".island"):
        if text(island.css_first("h2")) == "Upphovsrätt":
            details["rights"] = "\n\n".join(text(p) for p in island.css("p"))
    labels = dict(extract_categories(tree))
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
            except ValueError as error:
                raise PressImageError(
                    "Invalid portrait publication metadata"
                ) from error
    if details.get("updated") == details.get("published"):
        details.pop("updated", None)
    if "role" not in record and (role := text(body.css_first("p.ingress"))):
        details["role"] = role
    return details, labels, render_markdown(record, html)
