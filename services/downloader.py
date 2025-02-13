import urllib
import time

from services.selenium_driver import Selenium_Driver
from services.web_parser import get_document_list

REGERING_URL = "https://www.regeringen.se"
REGERING_QUERY_URL = REGERING_URL + "/Filter/GetFilteredItems?"


def parameters(page_size, page_number):
    params = {
        "lang": "sv",
        "filterType": "Taxonomy",
        "displayLimited": False,
        "pageSize": page_size,
        "page": page_number,
    }
    return urllib.parse.urlencode(params)


class Downloader(object):
    def __init__(self):
        self.d = Selenium_Driver()

    def get_amount(self):
        response = self.d.get_json(REGERING_QUERY_URL + parameters(1, 1))
        print(response)
        return response["TotalCount"]

    def get_latest_items(self, amount):
        if amount > 1000:
            print("Trying to fetch more than 1000 items, segmenting the requests...")
            page_size = 1000
        else:
            page_size = amount

        page_amount = amount // 1000 + 1

        latest_items = []
        codes = {}

        for page_number in range(1, page_amount + 1):
            page_items, page_codes = self.get_items_for_page(page_size, page_number)
            latest_items.extend(page_items)
            codes.update(page_codes)

        for i, item in enumerate(latest_items):
            if not item["published"] and i != 0:
                previous_item = latest_items[i - 1]
                latest_items[i]["published"] = (
                    previous_item["updated"]
                    if previous_item["updated"]
                    else previous_item["published"]
                )

        return latest_items, codes

    def get_items_for_page(self, page_size, page_number):
        print(f"Fetching page {page_number}...")
        url = REGERING_QUERY_URL + parameters(page_size, page_number)
        contents = self.d.get_json(url)

        data, codes = get_document_list(contents)

        if not data:
            print("Failed, retrying...")
            time.sleep(1)
            return self.get_items_for_page(page_size, page_number)

        return data, codes

    def get_webpage(self, path):
        return self.d.get(REGERING_URL + path)

    @staticmethod
    def last_updated(item):
        return (
            item["updated"]
            if "updated" in item and item["updated"]
            else item["published"]
        )
