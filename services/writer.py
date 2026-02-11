import csv
import json
from pathlib import Path


class Writer(object):
    @staticmethod
    def write_json(data, filename, indent=4):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=indent)

    @staticmethod
    def write_csv(data, filename):
        keys = data[0].keys()

        with open(filename, "w", newline="") as file:
            dict_writer = csv.DictWriter(file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    @staticmethod
    def write_md(data, filename):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        data = "\n".join([line.rstrip() for line in data.splitlines()]) + "\n"

        with open(filename, "w") as file:
            file.write(data)
