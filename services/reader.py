import json


def read_json(filename):
    with open(filename, "r") as file:
        return json.load(file)


# def read_jsons(directory):
#     for json_file in os.
#     with open(filename, "r") as file:
#         return json.load(file)
