"""JSON data shapes shared by chain parsing, reconciliation and publication."""

from collections.abc import Callable
from typing import NotRequired, Protocol, TypedDict

type RedirectResolver = Callable[[str], str]


class WebpageDownloader(Protocol):
    def get_webpage(self, path: str) -> str | None: ...


class Document(TypedDict):
    url: str
    title: str | None
    date: str | None
    current_page: bool


class PublishedDocument(Document):
    sources: list[str]


class Stage[DocumentType: Document](TypedDict):
    name: str | None
    documents: list[DocumentType]


class Actor[DocumentType: Document](TypedDict):
    name: str | None
    stages: list[Stage[DocumentType]]


class Phase[DocumentType: Document](TypedDict):
    name: str | None
    ongoing: bool | None
    actors: list[Actor[DocumentType]]


class HasPhases[DocumentType: Document](TypedDict):
    phases: list[Phase[DocumentType]]


class ObservationContent(HasPhases[Document]):
    # source includes the selector; item_url identifies the underlying page.
    source: str
    item_url: str
    parser_version: int
    celex: list[str]
    identity_celex: NotRequired[list[str]]


class Observation(ObservationContent):
    content_hash: str


class ExternalIds(TypedDict):
    celex: list[str]


class ChainRecord(HasPhases[PublishedDocument]):
    id: str
    external_ids: ExternalIds
    sources: list[str]


type Assignments = dict[str, str]
type Aliases = dict[str, list[str]]
type ChainGroups = dict[str, list[Observation]]
type ItemReferences = dict[str, set[str]]
type MembershipContext = tuple[str | None, str | None, str | None, str]


class ChainCollection(TypedDict):
    version: int
    chains: dict[str, ChainRecord]
    aliases: Aliases


class ChainState(TypedDict):
    version: int
    observations: dict[str, Observation]
    assignments: Assignments
    aliases: Aliases
    redirects: dict[str, str]
    completed: list[str]


class ChainItem(TypedDict):
    url: str
    chains: NotRequired[list[str]]


class Failure(TypedDict):
    source: str
    error: str


class AmbiguousMatch(TypedDict):
    url: str
    chains: list[str]


class PhaseConflict(TypedDict):
    chain: str
    phase: str | None
    sources: list[str]


class MembershipConflict(TypedDict):
    chain: str
    membership: list[str | None]
    sources: list[str]


type Conflict = PhaseConflict | MembershipConflict


class ChainReport(TypedDict):
    parser_failures: int
    ambiguous_matches: int
    conflicting_observations: int
    failures: list[Failure]
    ambiguous: list[AmbiguousMatch]
    conflicts: list[Conflict]
    recheck: list[str]
    observations: int
    chains: int
