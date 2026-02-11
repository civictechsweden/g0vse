import json
import time
import gc
from camoufox.sync_api import Camoufox
from playwright._impl._errors import TimeoutError, TargetClosedError
from playwright.sync_api import Page


class Browser:
    def __init__(self):
        self.cf = None
        self.browser = None
        self.request_count = 0
        self.restart()

    def _setup_context(self):
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

    def restart(self):
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.cf:
                self.cf.__exit__(None, None, None)
        except Exception:
            pass

        self.cf = Camoufox(geoip=True, headless=True)
        self.browser = self.cf.start()
        self._setup_context()
        self.request_count = 0
        gc.collect()

    def get(self, url, retries: int = 3):
        self.request_count += 1
        if self.request_count > 100:
            print("Periodic browser restart to free memory...")
            self.restart()

        for i in range(retries):
            try:
                self.page.goto(url, wait_until="domcontentloaded")
                source = self.page.content()

                if "You are unable to access" in source:
                    print("Blocked by Cloudflare, waiting 3 seconds...")
                    time.sleep(3)
                    continue
                elif "The service is unavailable." in source:
                    print("Page unavailable, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                elif "Sidan kan inte hittas" in source or "Något gick fel" in source:
                    print(f"404: Could not download file from {url}")
                    return None

                return source
            except (TimeoutError, TargetClosedError) as e:
                print(f"{type(e).__name__}, retrying ({i+1}/{retries}) in 3 s…")
                time.sleep(3)
                if isinstance(e, TargetClosedError):
                    self.restart()

        try:
            self.restart()
            self.page.goto(url, wait_until="domcontentloaded")
            return self.page.content()
        except (TimeoutError, TargetClosedError):
            print("Gave up after browser restart.")
            return None

    def get_json(self, url, retries: int = 3):
        self.request_count += 1
        if self.request_count > 100:
            print("Periodic browser restart to free memory...")
            self.restart()

        for i in range(retries):
            try:
                response = self.page.goto(url)
                if response:
                    return response.json() or {}
            except (TimeoutError, TargetClosedError) as e:
                print(f"{type(e).__name__} during JSON fetch, retrying ({i+1}/{retries}) in 3 s…")
                time.sleep(3)
                if isinstance(e, TargetClosedError):
                    self.restart()
            except json.decoder.JSONDecodeError:
                print("Invalid JSON payload, maybe Cloudflare?…")
                return {}
        return {}

    def __del__(self):
        try:
            if self.cf:
                self.cf.__exit__(None, None, None)
        except Exception:
            pass
