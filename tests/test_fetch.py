import errno
from copy import deepcopy

import fetch
from services.item_refresh import RefreshPlan


class Downloader:
    @staticmethod
    def get_webpage(url):
        return """
        <main>
          <div class="col-1">
            <h1><span class="h1-vignette">Test ID</span>Long URL</h1>
            <div class="cl"><p>Content.</p></div>
            <div class="list--icons">
              <a href="/contentassets/document.pdf">Document</a>
            </div>
          </div>
        </main>
        """


def test_process_item_keeps_metadata_when_markdown_filename_is_too_long(
    monkeypatch, tmp_path
):
    item = {
        "title": "Search title",
        "url": "/regeringsuppdrag/2026/06/" + "x" * 300 + "/",
        "types": [],
        "senders": [],
    }

    def raise_name_too_long(content, filename):
        raise OSError(errno.ENAMETOOLONG, "File name too long", filename)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fetch.Writer, "write_md", raise_name_too_long)

    assert fetch.process_item(item, Downloader(), {}) is fetch.ProcessingOutcome.CHANGED
    assert item["id"] == "Test ID"
    assert item["attachments"] == [
        {"name": "Document", "url": "/contentassets/document.pdf"}
    ]


def test_process_item_still_raises_other_write_errors(monkeypatch, tmp_path):
    item = {
        "title": "Search title",
        "url": "/regeringsuppdrag/2026/06/example/",
        "types": [],
        "senders": [],
    }

    def raise_disk_error(content, filename):
        raise OSError(errno.ENOSPC, "No space left", filename)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fetch.Writer, "write_md", raise_disk_error)

    try:
        fetch.process_item(item, Downloader(), {})
    except OSError as error:
        assert error.errno == errno.ENOSPC
    else:
        raise AssertionError("non-filename write errors must not be ignored")


def test_forced_refresh_does_not_rewrite_unchanged_markdown(monkeypatch, tmp_path):
    item = {
        "title": "Search title",
        "url": "/regeringsuppdrag/2026/06/example/",
        "types": [],
        "senders": [],
    }
    monkeypatch.chdir(tmp_path)

    assert fetch.process_item(item, Downloader(), {}) is fetch.ProcessingOutcome.CHANGED
    previous_item = deepcopy(item)
    markdown_path = tmp_path / "data/regeringsuppdrag/2026/06/example.md"

    def unexpected_write(content, filename):
        raise AssertionError("unchanged Markdown should not be rewritten")

    monkeypatch.setattr(fetch.Writer, "write_md", unexpected_write)

    outcome = fetch.process_item(
        item,
        Downloader(),
        {},
        existing_mds={"regeringsuppdrag/2026/06/example.md"},
        force_refresh=True,
        previous_item=previous_item,
    )

    assert markdown_path.exists()
    assert outcome is fetch.ProcessingOutcome.UNCHANGED


def test_forced_refresh_detects_markdown_only_changes(monkeypatch, tmp_path):
    item = {
        "title": "Search title",
        "url": "/regeringsuppdrag/2026/06/example/",
        "types": [],
        "senders": [],
    }
    monkeypatch.chdir(tmp_path)
    fetch.process_item(item, Downloader(), {})
    previous_item = deepcopy(item)
    markdown_path = tmp_path / "data/regeringsuppdrag/2026/06/example.md"
    markdown_path.write_text("Old content\n", encoding="utf-8")

    outcome = fetch.process_item(
        item,
        Downloader(),
        {},
        existing_mds={"regeringsuppdrag/2026/06/example.md"},
        force_refresh=True,
        previous_item=previous_item,
    )

    assert outcome is fetch.ProcessingOutcome.CHANGED
    assert "Content." in markdown_path.read_text(encoding="utf-8")


def test_changed_item_does_not_read_previous_markdown(monkeypatch, tmp_path):
    item = {
        "title": "Search title",
        "url": "/regeringsuppdrag/2026/06/example/",
        "types": [],
        "senders": [],
    }
    previous_item = {**item, "title": "Old title"}
    monkeypatch.chdir(tmp_path)

    def unexpected_read(self, *args, **kwargs):
        raise AssertionError("Markdown is unnecessary when the object changed")

    monkeypatch.setattr(fetch.Path, "read_text", unexpected_read)

    outcome = fetch.process_item(
        item,
        Downloader(),
        {},
        existing_mds={"regeringsuppdrag/2026/06/example.md"},
        force_refresh=True,
        previous_item=previous_item,
    )

    assert outcome is fetch.ProcessingOutcome.CHANGED


def test_process_all_items_promotes_only_changed_refreshes(monkeypatch, tmp_path):
    items = [{"url": "/new/"}, {"url": "/a/"}, {"url": "/b/"}, {"url": "/c/"}]
    previous_b = {"url": "/b/", "id": "B"}
    plan = RefreshPlan(
        candidate_order=["/new/", "/c/", "/b/"],
        force_refresh_urls={"/new/", "/c/", "/b/"},
        new_urls={"/new/"},
        previous_items={"/b/": previous_b, "/c/": {"url": "/c/"}},
    )
    outcomes = {
        "/new/": fetch.ProcessingOutcome.CHANGED,
        "/a/": fetch.ProcessingOutcome.SKIPPED,
        "/b/": fetch.ProcessingOutcome.FAILED,
        "/c/": fetch.ProcessingOutcome.CHANGED,
    }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        fetch,
        "process_item",
        lambda item, *args, **kwargs: outcomes[item["url"]],
    )

    result = fetch.process_all_items(items, object(), {}, plan)

    assert [item["url"] for item in result] == ["/new/", "/c/", "/a/", "/b/"]
    assert result[-1] is previous_b
