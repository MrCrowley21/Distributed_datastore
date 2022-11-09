import socket
import logging
import json
import random
import threading
from time import sleep
from copy import deepcopy

from config import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


class ServerCommunication:
    def __init__(self):
        self.app = None
        self.leader_value = random.randint(0, 100)
        self.leader_data = {}
        self.is_partition_leader = False
        self.partition_leader_exists = False

    def send_data(self, data, udp_to_send):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        prepared_data = json.dumps(data).encode('utf-8')
        try:
            sock.sendto(prepared_data, (ip, udp_to_send))
            logging.info('Sending UDP package to another server...')
        except:
            pass

    def receive_data(self, storage):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, udp_port))
        while True:
            data, address = sock.recvfrom(buffer_size)
            data = json.loads(data.decode('utf-8'))
            try:
                if data['leader'] == True:
                    self.partition_leader_exists = True
                else:
                    self.leader_data[data['port']] = data['leader']
                    logging.info(f'{len(self.leader_data)} {self.leader_data} {len(ports_to_send)}')
                    if len(self.leader_data) == len(ports_to_send):
                        self.find_partition_leader()
                    logging.info(f'Leader dict {self.leader_data}')
            except KeyError:
                storage.storage = deepcopy(data)
            logging.info(f'Receiving UDP package from another server...')
            logging.info(f'Received: {data}')

    def find_partition_leader(self):
        s = 0
        for i in self.leader_data:
            s += self.leader_data[i]
        partition_leader = s % len(self.leader_data)
        self.leader_data.clear()
        if server_id == partition_leader:
            self.is_partition_leader = True
            logging.info(f'Partition leader address: http://' + ip + ':' + str(port) + '/')
            threading.Thread(target=lambda: self.app.run(port=port, host="0.0.0.0", debug=True, use_reloader=False)).start()
        self.partition_leader_exists = True
        for destination_port in ports_to_send:
            self.send_data({'port': udp_port, 'leader': True}, destination_port)

    def set_partition_leader(self, app):
        self.app = app
        while True:
            if not self.partition_leader_exists:
                leader_data = {'port': udp_port, 'leader': self.leader_value}
                for destination_port in ports_to_send:
                    self.send_data(leader_data, destination_port)
                sleep(5)
