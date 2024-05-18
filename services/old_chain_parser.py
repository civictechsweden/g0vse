from .redirecter import get_final_url


def extract_old_chains(accordion_chain):
    headers = accordion_chain.select("h3")
    contents = accordion_chain.select("div")

    name = "Regeringen"

    items = []

    for header, content in zip(headers, contents):
        items.extend(extract_chain_items(header, content))

    ongoing = True

    return [{"ongoing": ongoing, "actors": [{"name": name, "steps": items}]}]


def extract_chain_items(header, content):
    items = []
    step = header.text.split(" (")[0]

    for item in content.select(".list--DateLinkDescr__listitem"):
        a = item.select_one("a")

        if a:
            url = (
                "current" if "aria-disabled" in a and a["aria-disabled"] else a["href"]
            )
            url = get_final_url(url) if ".aspx" in url else url
            name = a.text
        else:
            url = None
            name = None

        items.append(
            {
                "name": name,
                "step": step,
                "date": item.select_one("time")["datetime"],
                "url": url,
            }
        )

    return items
