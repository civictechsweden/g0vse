from service.writer import Writer
from service.downloader import Downloader

downloader = Downloader()

amount = downloader.get_amount()
print(f'Found {amount} documents on regeringen.se')

latest_items = downloader.get_latest_items(amount)

Writer.write_json(latest_items, 'items.json')
