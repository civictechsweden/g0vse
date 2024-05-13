from .redirecter import get_final_url

A = ".c-accordion"
L = ".c-list-content"


def extract_new_chains(soup):
    chains = []
    for accordion in soup.select(A):
        chain_name = soup.select_one(A + "-head__title").text
        ongoing = accordion.select_one(A + "-head__box") is not None
        actors = []

        for actor in accordion.select(A + "__items"):
            name = actor.select_one(A + "-plain__action").text.strip()
            items = [extract_chain_item(item) for item in actor.select(L)]

            actors.append({"name": name, "steps": items})

        chains.append({"name": chain_name, "ongoing": ongoing, "actors": actors})

    return chains


def extract_chain_item(item):
    step = item.select_one(L + "__title > strong")
    step = step.text if step else None
    date = item.select_one(L + "__date")
    date = date["datetime"] if date else None
    link = item.select_one(L + "__link")

    if link:
        name, url = link.text, link["href"]
        url = get_final_url(url) if ".aspx" in url else url
    else:
        name, url = None, None

        if item.select_one(L + "__item > p"):
            url = "current"

    return {"name": name, "step": step, "date": date, "url": url}
