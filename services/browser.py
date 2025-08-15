import json
import time
from camoufox.sync_api import Camoufox
from playwright._impl._errors import TimeoutError
from playwright.sync_api import Page


class Browser:
    def __init__(self):
        self.browser: Camoufox = Camoufox(geoip=True, headless=True).start()
        self.context = self.browser.new_context()
        self.page: Page = self.context.new_page()
        self.context.set_default_navigation_timeout(30_000)
        blocked = {"image", "stylesheet", "font", "media"}
        self.context.route(
            "**/*",
            lambda route, req: (
                route.abort() if req.resource_type in blocked else route.continue_()
            ),
        )

    def get(self, url, retries: int = 3):
        for _ in range(retries):
            try:
                self.page.goto(url, wait_until="domcontentloaded")
                source = self.page.content()

                if "You are unable to access" in source:
                    print("Blocked by Cloudflare, waiting 3 seconds...")
                    time.sleep(3)
                    continue  # ← no recursion
                elif "The service is unavailable." in source:
                    print("Page unavailable, waiting 60 seconds...")
                    time.sleep(60)
                    continue  # ← no recursion
                elif "Sidan kan inte hittas" in source or "Något gick fel" in source:
                    print(f"404: Could not download file from {url}")
                    return None

                return source
            except TimeoutError:
                print("Timeout, retrying in 3 s…")
                time.sleep(3)

        self.page.close()
        self.page = self.context.new_page()

        try:
            self.page.goto(url, wait_until="domcontentloaded")
            return self.page.content()
        except TimeoutError:
            print("Gave up after page rebuild.")
            return None

    def get_json(self, url):
        response = self.page.goto(url)

        try:
            return response.json() or {}
        except json.decoder.JSONDecodeError:
            print("Invalid JSON payload, maybe Cloudflare?…")
            print(response.text)
            return {}

    def __del__(self):
        try:
            if hasattr(self, "page") and not self.page.is_closed():
                self.page.close()
        except Exception:
            pass
        try:
            if hasattr(self, "request"):
                self.request.dispose()
        except Exception:
            pass
        if self.browser:
            self.browser.stop()
