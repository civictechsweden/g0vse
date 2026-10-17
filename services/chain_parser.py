"""Normalize a single selected source view, without guessing chain identity."""

import hashlib
import json
import re
from collections.abc import Iterator
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

from selectolax.parser import HTMLParser, Node

from services.chain_types import (
    Actor,
    Document,
    HasPhases,
    Observation,
    ObservationContent,
    Phase,
    RedirectResolver,
    Stage,
)

PARSER_VERSION = 1
ORIGIN = "https://www.regeringen.se"
LOCAL_HOSTS = {"regeringen.se", "www.regeringen.se", "g0v.se", "www.g0v.se"}


class ChainParseError(ValueError):
    pass


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def normalize_url(
    url: str,
    base: str = "/",
    resolve: RedirectResolver | None = None,
    view: bool = False,
) -> str:
    parts = urlsplit(urljoin(ORIGIN + base, url))
    if parts.scheme not in {"http", "https"}:
        raise ChainParseError(f"Unsupported document URL: {url}")
    if parts.hostname in LOCAL_HOSTS:
        if parts.path.lower().endswith(".aspx") or re.fullmatch(
            r"/t/\d+/sv/?", parts.path
        ):
            if resolve is None:
                raise ChainParseError(f"Unresolved legacy URL: {url}")
            target = resolve(urlunsplit(parts))
            if urlsplit(target).path == parts.path:
                raise ChainParseError(f"Unresolved redirect: {url}")
            return normalize_url(target, resolve=None, view=view)
        path = parts.path.rstrip("/")
        if not path.lower().endswith(
            (
                ".pdf",
                ".doc",
                ".docx",
                ".html",
                ".htm",
                ".xlsx",
                ".xml",
                ".json",
                ".txt",
                ".zip",
            )
        ):
            path += "/"
        if view:
            query = parse_qs(parts.query, keep_blank_values=True)
            if "id" in query:
                selector = ";".join(
                    sorted(filter(None, re.split(r"[;\s]+", query["id"][0])))
                )
                return path + "?" + urlencode({"id": selector})
        return path
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


def label(node: Node | None) -> str | None:
    return " ".join(node.text(separator=" ", strip=True).split()) if node else None


def date_in(node: Node) -> str | None:
    time = node.css_first("time")
    return time.attributes.get("datetime") if time else None


def document(
    node: Node, date: str | None, item_url: str, resolve: RedirectResolver | None
) -> Document:
    current = any(
        node.attributes.get(key) in {"true", "page"}
        for key in ("aria-current", "aria-disabled")
    )
    title_node = node.css_first("strong") if current else node
    return {
        "url": item_url
        if current
        else normalize_url(node.attributes["href"] or "", item_url, resolve),
        "title": label(title_node) or label(node),
        "date": date,
        "current_page": current,
    }


def legacy_phases(
    root: Node, item_url: str, resolve: RedirectResolver | None
) -> list[Phase[Document]]:
    stages: list[Stage[Document]] = []
    # DOM order, rather than zipping headings with arbitrary wrapper divs.
    for node in root.traverse():
        if node.tag == "h3":
            stages.append(
                {
                    "name": re.sub(r"\s*\(\d+ st\)\s*$", "", label(node) or ""),
                    "documents": [],
                }
            )
        elif (
            "list--DateLinkDescr__listitem"
            in (node.attributes.get("class") or "").split()
        ):
            if not stages:
                raise ChainParseError("Legacy documents have no stage")
            for link in node.css("a[href], a[aria-disabled=true]"):
                stages[-1]["documents"].append(
                    document(link, date_in(node), item_url, resolve)
                )
    if not stages:
        raise ChainParseError("Legacy chain has no headings")
    return [
        {
            "name": "Lagstiftning i Sverige",
            "ongoing": None,
            "actors": [{"name": "Regeringen", "stages": stages}],
        }
    ]


def document_date_in_block(node: Node, block: Node) -> str | None:
    """Use the nearest preceding time, falling back to the block's first date."""
    ancestor = node
    while ancestor and ancestor != block:
        sibling = ancestor.prev
        while sibling:
            if sibling.tag == "time":
                return sibling.attributes.get("datetime")
            sibling = sibling.prev
        ancestor = ancestor.parent
    return date_in(block)


def modern_phases(
    root: Node, item_url: str, resolve: RedirectResolver | None
) -> list[Phase[Document]]:
    phases: list[Phase[Document]] = []
    for accordion in root.css(".c-accordion"):
        heading = accordion.css_first(".c-accordion-head__title")
        if not heading:
            raise ChainParseError("Phase has no heading")
        actors: list[Actor[Document]] = []
        for actor in accordion.css(".c-accordion__items"):
            name = actor.css_first(".c-accordion-plain__action")
            if not name:
                raise ChainParseError("Actor has no heading")
            stages: list[Stage[Document]] = []
            for block in actor.css(".c-list-content"):
                stage = block.css_first(
                    ".c-list-content__title h4, .c-list-content__title > strong"
                )
                stage_name = label(stage)
                documents: list[Document] = []
                for node in block.css(
                    "a.c-list-content__link, [aria-current=true], [aria-current=page], a[aria-disabled=true]"
                ):
                    date = document_date_in_block(node, block)
                    documents.append(document(node, date, item_url, resolve))
                empty = any(
                    label(node) == "Inga dokument"
                    for node in block.css(".c-list-content__item > i")
                )
                if not documents and not empty:
                    raise ChainParseError("Unrecognized document/current-page markup")
                if stage is None and stages:
                    # SOU 2026:12 has a heading; SOU 2025:106 follows in a
                    # separate block without one. Both belong to the SOU stage.
                    stages[-1]["documents"].extend(documents)
                else:
                    stages.append({"name": stage_name, "documents": documents})
            if not stages:
                raise ChainParseError("Actor has no recognizable stages")
            actors.append({"name": label(name), "stages": stages})
        if not actors:
            raise ChainParseError("Phase has no actors")
        phases.append(
            {
                "name": label(heading),
                "ongoing": accordion.css_first(".c-accordion-head__box") is not None,
                "actors": actors,
            }
        )
    if not phases:
        raise ChainParseError("Chain has no phases")
    return phases


def extract_chains(
    html: str,
    item_url: str,
    source_view_url: str | None = None,
    resolve: RedirectResolver | None = None,
) -> tuple[Observation, list[str]]:
    """Return one observation plus same-page alternate views to fetch.

    Empty phases means a recognized page without a chain. Malformed chain
    markup raises instead of replacing a last successful observation.
    """
    tree = HTMLParser(html)
    item_url = normalize_url(item_url)
    source_view_url = normalize_url(source_view_url or item_url, view=True)
    old = tree.css_first("#accordion--chain")
    new = tree.css_first("nav.c-accordion-block")
    if old:
        phases = legacy_phases(old, item_url, resolve)
    elif new:
        phases = modern_phases(new, item_url, resolve)
    elif tree.css_first(".c-accordion, [id*=chain], [class*=chain]") or any(
        "lagstiftningskedj" in (label(heading) or "").lower()
        for heading in tree.css("h2, h3")
    ):
        raise ChainParseError("Unrecognized chain layout")
    elif tree.css_first("h1") and tree.css_first(".col-1"):
        phases = []
    else:
        raise ChainParseError("Not a recognized document page")
    choices = set()
    for link in tree.css(".c-accordion-content a[href]"):
        href = link.attributes.get("href") or ""
        if normalize_url(href, item_url) == item_url and "id" in parse_qs(
            urlsplit(href).query, keep_blank_values=True
        ):
            choices.add(normalize_url(href, item_url, view=True))
    query = parse_qs(urlsplit(source_view_url).query, keep_blank_values=True)
    selector = query.get("id", [""])[0]
    pattern = r"\b[0-9]{5}[A-Z]{1,2}[0-9]{4}\b"
    identity_celex = sorted(set(re.findall(pattern, selector)))
    if "id" not in query and phases and "inom EU" in (phases[0]["name"] or ""):
        identity_celex = sorted(
            {
                celex
                for actor in phases[0]["actors"]
                for stage in actor["stages"]
                for doc in stage["documents"]
                if "eur-lex.europa.eu" in doc["url"]
                for celex in re.findall(pattern, doc["url"])
            }
        )
    celex = sorted(
        set(identity_celex)
        | {
            celex
            for phase in phases
            for actor in phase["actors"]
            for stage in actor["stages"]
            for doc in stage["documents"]
            if "eur-lex.europa.eu" in doc["url"]
            for celex in re.findall(pattern, doc["url"])
        }
    )
    observation_content: ObservationContent = {
        "source": source_view_url,
        "item_url": item_url,
        "parser_version": PARSER_VERSION,
        "celex": celex,
        "identity_celex": identity_celex,
        "phases": phases,
    }
    observation: Observation = {
        **observation_content,
        "content_hash": digest(observation_content),
    }
    return observation, sorted(choices - {source_view_url})


def memberships[DocumentType: Document](
    observation: HasPhases[DocumentType],
) -> Iterator[tuple[str | None, str | None, str | None, DocumentType]]:
    for phase in observation["phases"]:
        for actor in phase["actors"]:
            for stage in actor["stages"]:
                for doc in stage["documents"]:
                    yield phase["name"], actor["name"], stage["name"], doc
