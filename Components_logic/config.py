import json
from json import load, loads, dump


class Config:
    def __get_data(self):
        with open('config/config.json') as json_file:
            data = load(json_file)
        return data

    def extract_data(self):
        data = self.__get_data()
        return data["server_id"], data["address"], data["state"], data["port"], data["udp_port"], data["tcp_port"], \
               data["buffer_size"], data["udp_ports_to_send"], data["tcp_ports_to_send"]
