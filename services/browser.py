import json
import time
from camoufox.sync_api import Camoufox
from playwright._impl._errors import TimeoutError
from playwright.sync_api import Page


class Browser:
    def __init__(self):
        self.browser: Camoufox = Camoufox(geoip=True, headless=True).start()

    def get(self, url):
        page: Page = self.browser.new_page()

        try:
            page.goto(url, timeout=10000)
            source = page.content()
        except TimeoutError:
            print("Timeout, waiting for 3 seconds...")
            time.sleep(3)
            return self.get(url)

        if "You are unable to access" in source:
            print("Blocked by Cloudflare, waiting 3 seconds...")
            time.sleep(3)
            return self.get(url)
        elif "The service is unavailable." in source:
            print("Page unavailable, waiting 60 seconds...")
            time.sleep(60)
            return self.get(url)
        elif "Sidan kan inte hittas" in source or "Något gick fel" in source:
            print(f"404: Could not download file from {url}")
            return None

        page.close()
        return source

    def get_json(self, url):
        page: Page = self.browser.new_page()
        response = page.goto(url)
        try:
            data = response.json()

            if not data:
                return {}

            page.close()
            return data
        except json.decoder.JSONDecodeError:
            print("Error with response, maybe blocked by Cloudflare...")
            print(response.text())
            return {}

    def __del__(self):
        if self.browser:
            self.browser.stop()
