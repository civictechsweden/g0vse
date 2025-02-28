import json
import time
from sys import platform
import zendriver as zd
from zendriver.core.connection import ProtocolException
from asyncio import TimeoutError


class ZenBrowser:
    def __init__(self):
        self.browser = None

    async def initialize_browser(self):
        if platform == "linux":
            browser_executable_path = "/usr/bin/google-chrome"
        else:
            browser_executable_path = None

        config = zd.Config(
            headless=True,
            browser_executable_path=browser_executable_path,
            sandbox=False,
            lang="sv-SE",
        )

        self.browser = await zd.Browser.create(config=config)

    async def stop_browser(self):
        await self.browser.stop()

    async def async_get(self, url):
        await self.initialize_browser()

        page = await self.browser.get(url)

        page_loading = True

        while page_loading:
            try:
                page_loading = False
                await page.select(".pagecontainer")
            except (ProtocolException, TimeoutError):
                await page.sleep(1)
                page_loading = True

        content = await page.get_content()

        await self.stop_browser()
        return content

    async def async_get_json(self, url):
        await self.initialize_browser()

        page = await self.browser.get(url)

        content = await page.get_content()
        await page

        if "Just a moment" in content:
            print("Waiting to be redirected from Cloudflare...")
            await page.wait(10)

        content = await page.get_content()
        await self.stop_browser()
        return content

    def get(self, url):
        source = zd.loop().run_until_complete(self.async_get(url))

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

        return source

    def get_json(self, url):
        response = zd.loop().run_until_complete(self.async_get_json(url))

        if not response:
            return {}

        try:
            return json.loads(response[response.index("{") : response.index("}") + 1])
        except json.decoder.JSONDecodeError:
            print("Error with response, maybe blocked by Cloudflare...")
            print(response)
            return {}

    def __del__(self):
        if self.browser:
            zd.loop().run_until_complete(self.browser.stop())
