"""Fetch calendar JSON, shared codes and Markdown without crawling ordinary pages."""

import argparse
from pathlib import Path

from services.calendar.export import prepare_calendar_export
from services.chains.export import publish_json
from services.downloader import Downloader
from services.reader import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Refetch historical event details too",
    )
    args = parser.parse_args()
    codes_path = args.data_dir / "api/codes.json"
    codes = read_json(codes_path) if codes_path.exists() else {}
    downloader = Downloader()
    try:
        files = {}
        if (
            prepare_calendar_export(
                downloader, codes, files, args.data_dir, force=args.refresh_all
            )
            is None
        ):
            return 1
        files["api/codes.json"] = {key: codes[key] for key in sorted(codes)}
        publish_json(files, args.data_dir)
        return 0
    finally:
        downloader.b.close()


if __name__ == "__main__":
    raise SystemExit(main())
