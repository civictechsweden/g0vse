"""JSON data shapes shared by chain parsing, reconciliation and publication."""

from collections.abc import Callable
from typing import Literal, NotRequired, Protocol, TypedDict

type RedirectResolver = Callable[[str], str]


class WebpageDownloader(Protocol):
    def get_webpage(self, path: str, /) -> str | None: ...


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


class ChainDocument(TypedDict):
    url: str
    title: NotRequired[str | None]
    date: NotRequired[str]
    inferred: NotRequired[Literal[True]]


class ChainStage(TypedDict):
    type: NotRequired[str]
    name: NotRequired[str]
    documents: list[ChainDocument]


class ChainActor(TypedDict):
    name: str | None
    stages: list[ChainStage]


class ChainPhase(TypedDict):
    name: str | None
    ongoing: NotRequired[bool]
    actors: list[ChainActor]


class ChainRecord(TypedDict):
    phases: list[ChainPhase]


type ChainGroups = dict[str, list[Observation]]
type ItemReferences = dict[str, set[str]]
type PublicIds = dict[str, str]
type MembershipContext = tuple[str | None, str | None, str | None, str]


class ChainCollection(TypedDict):
    chains: dict[str, ChainRecord]


class Failure(TypedDict):
    source: str
    error: str


class RecheckProgress(TypedDict):
    failures: list[Failure]
    recheck: list[str]


class Shortcut(TypedDict):
    name: str
    url: str


class ChainItem(TypedDict):
    url: str
    chains: NotRequired[list[str]]
    title: NotRequired[str | None]
    published: NotRequired[str | None]
    types: NotRequired[list[str]]
    senders: NotRequired[list[str]]
    id: NotRequired[str | None]
    shortcuts: NotRequired[list[Shortcut]]


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


class ChainReport(RecheckProgress):
    parser_failures: int
    ambiguous_matches: int
    conflicting_observations: int
    ambiguous: list[AmbiguousMatch]
    conflicts: list[Conflict]
    observations: int
    chains: int
    normalization: NotRequired[dict[str, int]]


class NormalizationFinding(TypedDict):
    id: str
    chain: str
    phase: str | None
    actor: str | None
    stage: str | None
    kind: str
    status: str
    before: str | None
    after: str | list[str] | None
    reason: str
    documents: list[str]
    document_title: str | None
    source: str
    departments: list[str]


class NormalizationReport(TypedDict):
    version: int
    summary: dict[str, int]
    findings: list[NormalizationFinding]
    recheck: list[str]
