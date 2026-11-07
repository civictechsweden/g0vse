"""Validate a whole portrait listing, then refresh its small set of detail pages."""

from urllib.parse import urlencode

from services.press_images.parser import (
    LISTING,
    ORIGIN,
    PressImageError,
    listing_root,
    parse_detail,
    parse_fragment,
    render_markdown,
)


def query_url(root):
    return (
        ORIGIN
        + "/Filter/GetFilteredItems?"
        + urlencode(
            {
                "lang": "sv",
                "filterType": "Structure",
                "filterByType": "PressImagePage",
                "rootPageReference": root,
                "sortAlphabetically": "True",
                "displayLimited": "False",
                "filterFromToday": "False",
                "page": 1,
                "pageSize": 1000,
            }
        )
    )


def fetch_listing(downloader):
    html = downloader.get_webpage(LISTING)
    if not html:
        raise PressImageError("Could not fetch the press-image directory")
    root, labels = listing_root(html)
    url = query_url(root)
    records = parse_fragment(downloader.b.get_json(url))
    if parse_fragment(downloader.b.get_json(url)) != records:
        raise PressImageError("Press-image listing changed during refresh")
    return records, labels


def refresh_details(downloader, records, labels, previous, root):
    result, markdown, failures = [], {}, []
    for row in records:
        path = root / (row["url"].strip("/") + ".md")
        try:
            html = downloader.get_webpage(row["url"])
            if not html:
                raise PressImageError("Could not download portrait detail")
            details, names, content = parse_detail(html, row)
            labels.update(names)
            result.append(row | details)
            markdown[row["url"]] = content
        except Exception as error:
            failures.append((row["url"], str(error)))
            old = previous.get(row["url"])
            result.append(old if old is not None else row)
            if not path.exists():
                markdown[row["url"]] = render_markdown(old or row)
    result.sort(key=lambda r: (r["department"], r["name"], r["url"]))
    return result, markdown, failures
