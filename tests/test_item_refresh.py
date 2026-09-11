from services.item_refresh import plan_incremental_refresh, promote_changed_items


def test_plan_refresh_preserves_positions_and_page_metadata():
    stored_items = [
        {"url": "/a/", "title": "A", "id": "A"},
        {
            "url": "/b/",
            "title": "Old B",
            "summary": "Old summary",
            "id": "B",
            "attachments": [{"name": "Stored attachment"}],
        },
        {"url": "/c/", "title": "C", "id": "C"},
    ]
    candidates = [
        {"url": "/new/", "title": "New"},
        {"url": "/b/", "title": "Fresh B"},
    ]

    items, plan = plan_incremental_refresh(stored_items, candidates)

    assert [item["url"] for item in items] == ["/new/", "/a/", "/b/", "/c/"]
    refreshed_b = items[2]
    assert refreshed_b["title"] == "Fresh B"
    assert "summary" not in refreshed_b
    assert refreshed_b["id"] == "B"
    assert refreshed_b["attachments"] == [{"name": "Stored attachment"}]
    assert plan.previous_items["/b/"] is stored_items[1]
    assert plan.new_urls == {"/new/"}
    assert plan.candidate_order == ["/new/", "/b/"]


def test_promote_changed_items_keeps_unchanged_relative_order():
    items = [
        {"url": "/a/"},
        {"url": "/b/"},
        {"url": "/c/"},
        {"url": "/d/"},
    ]

    result = promote_changed_items(
        items,
        candidate_order=["/d/", "/b/", "/c/"],
        changed_urls={"/d/", "/b/"},
    )

    assert [item["url"] for item in result] == ["/d/", "/b/", "/a/", "/c/"]


def test_promote_changed_items_preserves_duplicate_urls():
    first = {"url": "/duplicate/", "copy": 1}
    second = {"url": "/duplicate/", "copy": 2}

    result = promote_changed_items(
        [{"url": "/a/"}, first, {"url": "/b/"}, second],
        candidate_order=["/duplicate/"],
        changed_urls={"/duplicate/"},
    )

    assert result[:2] == [first, second]
