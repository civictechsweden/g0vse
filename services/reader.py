import json


def read_json(filename):
    with open(filename, "r") as file:
        return json.load(file)
