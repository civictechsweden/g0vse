from services.browser import Browser


def test_browser_recovery():
    b = Browser()
    print("Fetching first page...")
    res = b.get("https://www.regeringen.se/")
    assert res is not None, "Failed to fetch first page"
    print("Success fetching first page")

    print("Simulating browser crash (closing browser)...")
    b.browser.close()

    print("Fetching second page (should trigger restart)...")
    res = b.get("https://www.regeringen.se/pressmeddelanden/")
    assert res is not None, "Failed to recover after browser crash"
    print("Success fetching second page after recovery")

if __name__ == "__main__":
    test_browser_recovery()
