import pytest
import json
from services.downloader import Downloader
from services.web_parser import extract_page

def load_test_cases():
    with open("tests/test_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def downloader():
    return Downloader()

@pytest.mark.parametrize("expected", load_test_cases())
def test_parser_against_live_site(downloader, expected):
    url = expected["url"]
    print(f"\nTesting URL: {url}")
    
    # 1. Fetch live page
    page_content = downloader.get_webpage(url)
    assert page_content is not None, f"Failed to download {url}"
    
    # 2. Parse live page
    md_content, metadata = extract_page(page_content)
    
    # 3. Compare with expected data
    # Note: We compare specific fields that are likely to be stable
    assert metadata is not None, f"Parser returned None for {url}"
    
    # Title check
    expected_title = expected.get("title")
    actual_title = metadata.get("title")
    
    if not actual_title and md_content:
        actual_title = md_content.split("\n")[0].replace("# ", "")
        
    assert actual_title == expected_title, f"Title mismatch for {url}. Expected '{expected_title}', got '{actual_title}'"
    
    # ID check (if expected)
    if expected.get("id"):
        assert metadata.get("id") == expected.get("id"), f"ID mismatch for {url}"
        
    # Attachments check (count and names)
    expected_attachments = expected.get("attachments", [])
    actual_attachments = metadata.get("attachments", [])
    
    assert len(actual_attachments) == len(expected_attachments), \
        f"Attachment count mismatch for {url}. Expected {len(expected_attachments)}, got {len(actual_attachments)}"
        
    for i in range(len(expected_attachments)):
        assert actual_attachments[i]["name"] == expected_attachments[i]["name"], \
            f"Attachment name mismatch at index {i} for {url}"
            
    # Shortcuts check
    expected_shortcuts = expected.get("shortcuts", [])
    actual_shortcuts = metadata.get("shortcuts", [])
    
    assert len(actual_shortcuts) == len(expected_shortcuts), \
        f"Shortcut count mismatch for {url}. Expected {len(expected_shortcuts)}, got {len(actual_shortcuts)}"