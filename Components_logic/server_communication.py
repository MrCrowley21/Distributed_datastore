import socket
import logging
import random
import threading
from time import sleep
from copy import deepcopy
import json

from config.config import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


# class that defines communication of servers
class ServerCommunication:
    def __init__(self):
        self.app = None  # flask app
        self.leader_value = random.randint(0, 100)  # the value to determine the leader
        self.leader_data = {}  # the leader address
        self.is_partition_leader = False  # the state if is leader partition
        self.partition_leader_exists = False  # the state if partition leader exists

    # send data through UDP
    def send_data(self, data, udp_to_send):
        # initiate UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # encode data
        prepared_data = json.dumps(data).encode('utf-8')
        # send data
        try:
            sock.sendto(prepared_data, (ip, udp_to_send))
            logging.info('Sending UDP package to another server...')
        except:
            pass

    # receive data through UDP
    def receive_data(self, storage):
        # initiate UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, udp_port))
        # always receiving
        while True:
            # receive and decode data
            data, address = sock.recvfrom(buffer_size)
            data = json.loads(data.decode('utf-8'))
            # if information about leader
            try:
                if data['leader'] == True:
                    self.partition_leader_exists = True
                else:
                    self.leader_data[data['port']] = data['leader']
                    logging.info(f'{len(self.leader_data)} {self.leader_data} {len(ports_to_send)}')
                    if len(self.leader_data) == len(ports_to_send):
                        self.find_partition_leader()
                    logging.info(f'Leader dict {self.leader_data}')
            #  if any other data sent through UDP
            except KeyError:
                # update the state of local storage
                storage.storage = deepcopy(data)
            logging.info(f'Receiving UDP package from another server...')
            logging.info(f'Received: {data}')

    # find the partition leader if exist or set the existing one
    def find_partition_leader(self):
        # compute value to set the partition leader (random)
        s = 0
        for i in self.leader_data:
            s += self.leader_data[i]
        partition_leader = s % len(self.leader_data)
        # clear the partition leader data (in case it is down and substitution is needed)
        self.leader_data.clear()
        # if leaser set as it is
        if server_id == partition_leader:
            self.is_partition_leader = True
            logging.info(f'Partition leader address: http://' + ip + ':' + str(port) + '/')
            # initiate flask app and HTTP requests
            threading.Thread(target=lambda: self.app.run(port=port, host="0.0.0.0", debug=True, use_reloader=False)).start()
        # update info about the existence of partition leader
        self.partition_leader_exists = True
        for destination_port in ports_to_send:
            self.send_data({'port': udp_port, 'leader': True}, destination_port)

    # set partition leader if it does not exist
    def set_partition_leader(self, app):
        self.app = app  # define flask app
        while True:
            # in case no partition leader
            if not self.partition_leader_exists:
                # send data to se partition leader
                leader_data = {'port': udp_port, 'leader': self.leader_value}
                for destination_port in ports_to_send:
                    self.send_data(leader_data, destination_port)
                sleep(5)
