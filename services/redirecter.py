import urllib.request
from urllib.parse import urljoin

from fake_useragent import UserAgent

REGERING_URL = "https://www.regeringen.se"


def get_final_url(url):
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    opener.addheaders = [("User-Agent", UserAgent().random)]

    request = urllib.request.Request(urljoin(REGERING_URL, url), method="HEAD")

    with opener.open(request, timeout=30) as response:
        final_url = response.geturl()

    return final_url
