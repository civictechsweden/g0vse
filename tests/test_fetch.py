import errno

import fetch


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

    assert fetch.process_item(item, Downloader(), {})
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
