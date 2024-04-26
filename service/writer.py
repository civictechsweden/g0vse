import csv
import json

class Writer(object):
    @staticmethod
    def write_json(dict, filename):
        with open(filename, 'w') as fp:
            json_string = json.dumps(dict, ensure_ascii=False,
                                     indent=4).encode('utf-8')
            fp.write(json_string.decode())

    @staticmethod
    def write_csv(dict, filename):
        keys = dict[0].keys()

        with open(filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(dict)
