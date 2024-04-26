import urllib

from service.selenium_driver import Selenium_Driver
from service.web_parser import WebParser

REGERING_URL = "https://www.regeringen.se"
REGERING_QUERY_URL = REGERING_URL + "/Filter/GetFilteredItems?"

def parameters(page_size, page_number):
    params = {
        "lang": "sv",
        "filterType": "Taxonomy",
        "displayLimited": True,
        "pageSize": page_size,
        "page": page_number,
    }
    return urllib.parse.urlencode(params)


class Downloader(object):
    def __init__(self):
        self.d = Selenium_Driver()

    def get_amount(self):
        response = self.d.get_json(REGERING_QUERY_URL + parameters(1, 1))

        return response["TotalCount"]

    def get_latest_items(self, amount):
        if amount > 1000:
            print('Trying to fetch more than 1000 items, segmenting the requests...')
            page_size = 1000
        else:
            page_size = amount

        page_amount = amount // 1000 + 1

        latest_items = []

        for page_number in range(1, page_amount + 1):
            latest_items.extend(self.get_items_for_page(page_size, page_number))

        return latest_items

    def get_items_for_page(self, page_size, page_number):
        print(f'Fetching page {page_number}...')
        url = REGERING_QUERY_URL + parameters(page_size, page_number)
        contents = self.d.get_json(url)

        return WebParser.get_document_list(contents)
