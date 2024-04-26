from service.writer import Writer
from service.downloader import Downloader

downloader = Downloader()

amount = downloader.get_amount()
print(f'Found {amount} documents on regeringen.se')

latest_items, codes = downloader.get_latest_items(amount)
codes = { key: codes[key] for key in sorted(codes) }

Writer.write_json(latest_items, 'items.json')
Writer.write_json(codes, 'codes.json')

