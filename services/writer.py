import csv
import json
import subprocess
import sysconfig
from pathlib import Path


class Writer(object):
    @staticmethod
    def write_json(data, filename, indent=4):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=indent)
            file.write("\n")

    @staticmethod
    def write_csv(data, filename):
        keys = data[0].keys()

        with open(filename, "w", newline="") as file:
            dict_writer = csv.DictWriter(file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    @staticmethod
    def format_md(data):
        """Use the project formatter for both comparison and publication."""
        result = subprocess.run(
            [
                str(Path(sysconfig.get_path("scripts")) / "rumdl"),
                "fmt",
                "--stdin",
                "--silent",
                "--config",
                str(Path(__file__).resolve().parents[1] / "pyproject.toml"),
            ],
            input=data,
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout

    @staticmethod
    def write_md(data, filename):
        """Write Markdown already formatted by format_md."""
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as file:
            file.write(data)
