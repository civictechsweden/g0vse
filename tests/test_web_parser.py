from services.web_parser import extract_page


def test_extract_page_with_current_html_to_markdown_result():
    html = """
    <main>
      <div class="col-1">
        <h1>Example page</h1>
        <div class="cl"><p>Page content.</p></div>
        <div class="list--icons">
          <div><a href="/contentassets/example/document.pdf">Document (pdf 1 MB)</a></div>
        </div>
      </div>
    </main>
    """

    markdown, metadata = extract_page(html)

    assert markdown == "# Example page\n\nPage content.\n"
    assert metadata["attachments"] == [
        {
            "name": "Document (pdf 1 MB)",
            "url": "/contentassets/example/document.pdf",
        }
    ]
