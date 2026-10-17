"""Explicit document-type rules and conservative stage-name normalization.

Only newly assembled public records are changed. Source observations remain
intact. Unknown URLs and conflicting evidence never inherit a majority type.
A document type is not evidence of an actor or a completed process.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlsplit

from services.chains.diagnostics import FindingContext, NormalizationLog
from services.chains.parser import normalize_url
from services.chains.types import (
    ChainCollection,
    ChainItem,
    ChainStage,
    NormalizationReport,
    Phase,
    PublishedDocument,
)

LOCAL_URL_TYPES = {
    "/rattsliga-dokument/kommittedirektiv/": "1327",
    "/rattsliga-dokument/departementsserien-och-promemorior/": "1325",
    "/rattsliga-dokument/statens-offentliga-utredningar/": "1331",
    "/rattsliga-dokument/lagradsremiss/": "2085",
    "/rattsliga-dokument/proposition/": "1329",
    "/rattsliga-dokument/skrivelse/": "1330",
    "/remisser/": "2099",
    "/rapporter/": "1341",
    "/regeringsuppdrag/": "1342",
    "/faktapromemoria/": "2540",
    "/kommenterade-dagordningar/": "2098",
}

# Sector matters: e.g. 3R is a regulation, whereas 5PC is a proposal. References:
# https://eur-lex.europa.eu/content/help/eurlex-content/celex-number.html
# https://eur-lex.europa.eu/content/tools/TableOfSectors/types_of_documents_in_eurlex.html
CELEX_TYPES = {
    "3R": "eu-forordning",
    "3L": "eu-direktiv",
    "3D": "eu-beslut",
    "3F": "eu-rambeslut",
    "3H": "eu-rekommendation",
    "5PC": "eu-forslag",
    "5AP": "eu-parlamentsposition",
    "5AG": "eu-radsposition",
    "5DC": "eu-kommissionsdokument",
    "5XC": "eu-kommissionsdokument",
    "5SC": "eu-arbetsdokument",
    "5JC": "eu-join-dokument",
    "5AE": "eu-yttrande",
    "5AA": "eu-yttrande",
    "5IR": "eu-yttrande",
    "5IP": "eu-parlamentsresolution",
}

TYPE_NAMES = {
    "1327": "Kommittédirektiv",
    "1325": "Departementsserien och promemorior",
    "1331": "Statens offentliga utredningar",
    "2085": "Lagrådsremiss",
    "1329": "Proposition",
    "1330": "Skrivelse",
    "2099": "Remiss",
    "1341": "Rapport",
    "1342": "Regeringsuppdrag",
    "2540": "Faktapromemoria",
    "2098": "Kommenterad dagordning",
    "sfs": "Svensk författningssamling",
    "riksdagsbetankande": "Riksdagens betänkande",
    "riksdagsbeslut": "Riksdagsbeslut",
    "eu-forordning": "EU-förordning",
    "eu-direktiv": "EU-direktiv",
    "eu-beslut": "EU-beslut",
    "eu-rambeslut": "EU-rambeslut",
    "eu-rekommendation": "EU-rekommendation",
    "eu-forslag": "EU-förslag",
    "eu-parlamentsposition": "Europaparlamentets lagstiftningsposition",
    "eu-radsposition": "Rådets position",
    "eu-kommissionsdokument": "Övrigt kommissionsdokument",
    "eu-arbetsdokument": "Kommissionens arbetsdokument",
    "eu-join-dokument": "JOIN-dokument",
    "eu-yttrande": "EU-yttrande",
    "eu-parlamentsresolution": "Europaparlamentets resolution",
}

STAGE_NAME_TYPES = {name: code for code, name in TYPE_NAMES.items()}
STAGE_NAME_TYPES.update(
    {
        "Tilläggsdirektiv": "1327",
        "Departementsserien": "1325",
        "Promemoria": "1325",
        "Remiss SOU": "2099",
        "Remiss Ds": "2099",
        "Remisser": "2099",
        "Svensk författningssamling (SFS)": "sfs",
        "EU-Direktiv": "eu-direktiv",
        "EU-direktiv (EUR-Lex)": "eu-direktiv",
        "EU-förordningar": "eu-forordning",
    }
)


@dataclass(frozen=True)
class TypeInference:
    type: str | None
    reason: str
    candidates: tuple[str, ...] = ()


def stage_type_from_name(name: str | None) -> str | None:
    cleaned = re.sub(
        r"\s*\(\s*\d+\s*(?:st)?\s*\)\s*$", "", (name or "").replace("\xad", "")
    )
    return STAGE_NAME_TYPES.get(cleaned)


def type_from_url(url: str) -> str | None:
    """Classify a specific document URL, never an entire external domain."""
    parts = urlsplit(url)
    if parts.scheme and (
        parts.scheme not in {"http", "https"} or parts.hostname is None
    ):
        return None
    host = (parts.hostname or "").removeprefix("www.")
    path = unquote(parts.path)
    if not host or host in {"regeringen.se", "g0v.se"}:
        for prefix, document_type in LOCAL_URL_TYPES.items():
            if path.startswith(prefix) and path[len(prefix) :].strip("/"):
                return document_type
        return None
    if host == "svenskforfattningssamling.se":
        if re.fullmatch(
            r"/doc/\d{5,}\.(?:html|pdf)", path, re.IGNORECASE
        ) or re.fullmatch(
            r"/sites/default/files/sfs/\d{4}-\d{2}/SFS\d{4}-\d+\.pdf",
            path,
            re.IGNORECASE,
        ):
            return "sfs"
    elif host == "rkrattsbaser.gov.se":
        bet = parse_qs(parts.query).get("bet", [])
        if path.rstrip("/") in {"/sfst", "/sfsr"} and len(bet) == 1:
            if re.fullmatch(r"\d{4}:\d+", bet[0]):
                return "sfs"
    elif host == "rkrattsdb.gov.se":
        if re.fullmatch(r"/SFSdoc/\d{2}/\d+\.pdf", path, re.IGNORECASE):
            return "sfs"
    elif host == "riksdagen.se":
        match = re.fullmatch(
            r"/sv/(?:dokument-och-lagar/dokument|dokument-lagar/(?:arende|dokument))"
            r"/(betankande|proposition|skrivelse|riksdagsskrivelse)/[^/]+(?:/html)?/?",
            path,
        )
        if match:
            return {
                "betankande": "riksdagsbetankande",
                "proposition": "1329",
                "skrivelse": "1330",
                "riksdagsskrivelse": "riksdagsbeslut",
            }[match[1]]
        # Older migrated links omit the document-type segment. 01 is the
        # committee-report identifier found in those links in this corpus.
        if re.fullmatch(
            r"/sv/dokument-och-lagar/dokument/_[a-z0-9]{2}01[a-zåäö0-9]+/?",
            path,
            re.IGNORECASE,
        ):
            return "riksdagsbetankande"
    elif host == "eur-lex.europa.eu":
        uri = parse_qs(parts.query).get("uri", [])
        if len(uri) == 1 and path.startswith("/legal-content/"):
            celex = re.fullmatch(
                r"CELEX:([0-9])\d{4}([A-Z]{1,3})\d{4,}(?:R?\(\d+\))?(?:\.[A-Z]{3})?",
                uri[0],
                re.IGNORECASE,
            )
            if celex:
                return CELEX_TYPES.get(celex[1] + celex[2].upper())
        eli = re.fullmatch(
            r"/eli/(reg(?:_impl|_del)?|dir(?:_impl|_del)?|dec(?:_impl|_del)?)"
            r"/\d{4}/\d+/[^/]+(?:/[^/]+)*/?",
            path,
        )
        if eli:
            return {"reg": "eu-forordning", "dir": "eu-direktiv", "dec": "eu-beslut"}[
                eli[1].split("_")[0]
            ]
    return None


def infer_document_type(url: str, item_types: Iterable[str] = ()) -> TypeInference:
    """Use item metadata and URL rules as independent, checked evidence."""
    url_type = type_from_url(url)
    known_items = set(item_types) & set(LOCAL_URL_TYPES.values())
    candidates = tuple(sorted(known_items | ({url_type} if url_type else set())))
    if len(known_items) > 1:
        return TypeInference(None, "item_type_conflict", candidates)
    if known_items and url_type and url_type not in known_items:
        return TypeInference(None, "item_url_conflict", candidates)
    if known_items:
        return TypeInference(next(iter(known_items)), "item", candidates)
    return TypeInference(url_type, "url" if url_type else "unknown", candidates)


def infer_stage_type(documents: Iterable[TypeInference]) -> TypeInference:
    """Suggest one stage type only when every document has a compatible type.

    Committee reports belong to the site's Riksdagsbeslut display group, but
    their presence does not prove that Parliament has taken a decision.
    """
    documents = list(documents)
    if not documents:
        return TypeInference(None, "empty")
    candidates = tuple(
        sorted(
            {
                "riksdagsbeslut" if doc.type == "riksdagsbetankande" else doc.type
                for doc in documents
                if doc.type is not None
            }
        )
    )
    if any(doc.type is None for doc in documents):
        return TypeInference(None, "partial" if candidates else "unknown", candidates)
    if len(candidates) > 1:
        return TypeInference(None, "mixed", candidates)
    return TypeInference(candidates[0], "uniform", candidates)


def normalize_chain_records(
    collection: ChainCollection,
    evidence: dict[str, list[Phase[PublishedDocument]]],
    items: list[ChainItem],
    codes: dict[str, str],
) -> NormalizationReport:
    """Normalize odd named stages, retaining order, documents and source proof.

    Known stage types and unheaded EU groups keep their existing meaning.
    Multiple known types split into consecutive runs, rather than reordering
    documents or assigning a majority type to the entire stage.
    """
    item_index = {normalize_url(item["url"]): item for item in items}
    log = NormalizationLog(item_index, codes)
    guesses: dict[str, TypeInference] = {}

    def guess(url: str) -> TypeInference:
        if url not in guesses:
            item = item_index.get(normalize_url(url), {})
            guesses[url] = infer_document_type(url, item.get("types", []))
        return guesses[url]

    def type_name(code: str) -> str:
        return TYPE_NAMES.get(code, code)

    for chain_id, chain in collection["chains"].items():
        for phase, raw_phase in zip(chain["phases"], evidence[chain_id], strict=True):
            for actor, raw_actor in zip(
                phase["actors"], raw_phase["actors"], strict=True
            ):
                actor_context = FindingContext(chain_id, phase["name"], actor["name"])
                actor_documents = [
                    d for s in raw_actor["stages"] for d in s["documents"]
                ]
                if actor["name"] not in {
                    "Regeringen",
                    "EU-kommissionen",
                    "Europaparlamentet",
                    "Ministerrådet",
                    "Riksdagen",
                }:
                    log.add(
                        actor_context,
                        "actor_group",
                        actor["name"],
                        None,
                        "This source heading is a group rather than a recognized institution; document type alone cannot establish the actor.",
                        actor_documents,
                    )
                stages: list[ChainStage] = []
                for stage, raw_stage in zip(
                    actor["stages"], raw_actor["stages"], strict=True
                ):
                    documents = raw_stage["documents"]
                    context = FindingContext(
                        chain_id, phase["name"], actor["name"], raw_stage["name"]
                    )
                    for document in documents:
                        item = item_index.get(normalize_url(document["url"]), {})
                        date = document["date"]
                        published = item.get("published")
                        if date and published and date[:10] != published[:10]:
                            log.add(
                                context,
                                "date_discrepancy",
                                date,
                                published,
                                "Chain date differs from item publication date; clarify the date's meaning before changing it.",
                                [document],
                            )
                        inferred = guess(document["url"])
                        if inferred.reason in {
                            "item_url_conflict",
                            "item_type_conflict",
                        }:
                            log.add(
                                context,
                                "document_type_conflict",
                                type_name(type_from_url(document["url"]) or "unknown"),
                                [type_name(t) for t in inferred.candidates],
                                "Indexed item types and URL evidence disagree; no automatic type is assigned.",
                                [document],
                            )
                    inferred_stage = infer_stage_type(
                        guess(url) for url in dict.fromkeys(d["url"] for d in documents)
                    )
                    if "type" in stage:
                        if inferred_stage.type and inferred_stage.type != stage["type"]:
                            log.add(
                                context,
                                "stage_type_disagreement",
                                raw_stage["name"],
                                type_name(inferred_stage.type),
                                "A recognized process heading differs from linked document types; the heading is retained for review.",
                                documents,
                            )
                        stages.append(stage)
                        continue
                    if not stage.get("name"):
                        stages.append(stage)
                        continue
                    if inferred_stage.type:
                        stages.append(
                            {
                                "type": inferred_stage.type,
                                "documents": stage["documents"],
                            }
                        )
                        log.normalized_stages += 1
                        log.add(
                            context,
                            "normalized_stage",
                            raw_stage["name"],
                            type_name(inferred_stage.type),
                            "Every linked document has this compatible type. Source subtypes/roles may be more specific.",
                            documents,
                            status="normalized",
                        )
                    elif inferred_stage.reason == "mixed":
                        parts: list[ChainStage] = []
                        for document in stage["documents"]:
                            document_type = infer_stage_type(
                                [guess(document["url"])]
                            ).type
                            assert document_type is not None
                            if not parts or parts[-1].get("type") != document_type:
                                parts.append({"type": document_type, "documents": []})
                            parts[-1]["documents"].append(document)
                        stages.extend(parts)
                        log.split_stages += 1
                        log.add(
                            context,
                            "split_stage",
                            raw_stage["name"],
                            [type_name(part["type"]) for part in parts],
                            "Mixed document types split into consecutive stages, preserving document order.",
                            documents,
                            status="normalized",
                        )
                    else:
                        stages.append(stage)
                        log.add(
                            context,
                            "unresolved_stage",
                            raw_stage["name"],
                            None,
                            f"Incomplete or conflicting document evidence ({inferred_stage.reason}); original heading retained.",
                            documents,
                        )
                actor["stages"] = stages
    return log.report()
