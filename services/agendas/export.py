"""Prepare agenda JSON and repair weekly Markdown only after a complete traversal."""

import os
from pathlib import Path

from services.agendas.fetcher import AgendaExport, fetch_agendas
from services.agendas.parser import AgendaError
from services.web_parser import extract_page
from services.writer import Writer


def prepare_agenda_export(downloader, codes, files, root="data") -> AgendaExport | None:
    try:
        export = fetch_agendas(downloader, codes)
    except AgendaError as error:
        prefix = "::warning::" if os.environ.get("GITHUB_ACTIONS") else ""
        print(
            f"{prefix}Regeringsärenden refresh failed; keeping the previous export: {error}"
        )
        return None

    markdown = {}
    for source, html in export.pages.items():
        content, _ = extract_page(html, source)
        if content is None:
            raise AgendaError(f"Could not render weekly agenda {source}")
        markdown[source] = Writer.format_md(content)
    for source, content in markdown.items():
        path = Path(root) / (source.strip("/") + ".md")
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            Writer.write_md(content, path)

    codes.update(export.labels)
    files["api/regeringsarenden.json"] = export.records
    print(
        f"Regeringsärenden: {len(export.records):,} planned entries; "
        f"{len(export.undated_sources)} weekly sources with unverifiable meeting dates."
    )
    if export.undated_sources:
        print(
            "Unverifiable dates (first 5 sources): "
            + ", ".join(export.undated_sources[:5])
        )
    return export
