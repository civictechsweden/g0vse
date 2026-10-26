"""Fetch portrait metadata, shared codes and Markdown without crawling ordinary pages."""

import argparse
from pathlib import Path

from services.chains.export import publish_json
from services.downloader import Downloader
from services.press_images.export import prepare_press_image_export
from services.reader import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    codes_path = args.data_dir / "api/codes.json"
    codes = read_json(codes_path) if codes_path.exists() else {}
    downloader = Downloader()
    try:
        files = {}
        if prepare_press_image_export(downloader, codes, files, args.data_dir) is None:
            return 1
        files["api/codes.json"] = {key: codes[key] for key in sorted(codes)}
        publish_json(files, args.data_dir)
        return 0
    finally:
        downloader.b.close()


if __name__ == "__main__":
    raise SystemExit(main())
