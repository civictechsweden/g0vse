import json
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver import ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

from fake_useragent import UserAgent

DOWNLOAD_DIR_MAC = './tmp'

def wait_for_downloads():
    time.sleep(1)
    while any([filename.endswith('.crdownload') for filename in
               os.listdir(DOWNLOAD_DIR_MAC)]):
        time.sleep(1)


class Selenium_Driver(object):

    def __init__(self):
        options = ChromeOptions()
        userAgent = UserAgent().random
        options.add_argument(f'user-agent = { userAgent }')
        options.add_argument('--headless=chrome')
        options.add_experimental_option('prefs',  {
            'download.default_directory': DOWNLOAD_DIR_MAC,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'plugins.always_open_pdf_externally': True
            }
        )

        self.d = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    def get(self, url):
        self.d.get(url)
        return self.d.page_source

    def get_json(self, url):
        response = self.get(url)

        try:
            return json.loads(response[response.index('{'):response.index('}') + 1])
        except json.decoder.JSONDecodeError:
            print('Error with response, maybe blocked by Cloudflare...')
            return {}

    def get_file(self, url):
        self.d.get(url)
        wait_for_downloads()

        if 'Sidan kan inte hittas' in self.d.title:
            print(f'404: Could not download file from {url}')
            return None

        filename = url.split('/')[-1]
        filepath = filename

        print(f'Downloaded {filename}')
        return filepath

