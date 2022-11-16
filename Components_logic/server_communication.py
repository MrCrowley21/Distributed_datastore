import socket
import logging
import random
import threading
from threading import Lock
from time import sleep
from copy import deepcopy
import json
from json import load, loads, dumps

from Components_logic.config import Config

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
        self.server_id, self.address, self.port, self.udp_port, self.buffer_size, self.ports_to_send = \
            Config().extract_data()
        self.lock = Lock()

    # send data through UDP
    def send_data(self, data, udp_to_send):
        # initiate UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((self.address, self.port))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # encode data
        prepared_data = dumps(data).encode('utf-8')
        # send data
        try:
            sock.sendto(prepared_data, (self.address, udp_to_send))
            logging.info(f'Sending UDP package to another server... port: {udp_to_send}')
        except:
            pass

    # receive data through UDP
    def receive_data(self, storage):
        # initiate UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hostname = socket.gethostname()
        self.address = socket.gethostbyname(hostname)[:-1] + '1'
        sock.bind(('', self.udp_port))
        # always receiving
        while True:
            logging.info(f'Setting up the socket to receive data...')
            # receive and decode data
            data, address = sock.recvfrom(self.buffer_size)
            data = loads(data.decode('utf-8'))
            # if information about leader
            logging.info(f'Receiving UDP package from another server...')
            logging.info(f'Received: {data}')
            try:
                if data['leader'] == True:
                    logging.info(f'Receiving info about partition leader being chosen...')
                    self.partition_leader_exists = True
                else:
                    logging.info(f'Receiving data about partition leader...')
                    self.leader_data[data['port']] = data['leader']
                    logging.info(f'{len(self.leader_data)} {self.leader_data} {len(self.ports_to_send)}')
                    if len(self.leader_data) == len(self.ports_to_send):
                        self.find_partition_leader()
            #  if any other data sent through UDP
            except:
                logging.info(f'Modifying the data storage state...')
                # update the state of local storage
                storage.storage = deepcopy(data)

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
        if self.server_id == partition_leader:
            self.lock.acquire()
            self.is_partition_leader = True
            # update info about the existence of partition leader
            self.partition_leader_exists = True
            self.lock.release()
            for destination_port in self.ports_to_send:
                self.send_data({'port': self.udp_port, 'leader': True}, destination_port)
            logging.info(f'Partition leader address: http://127.0.0.1:' + str(self.port) + '/')
            # initiate flask app and HTTP requests
            threading.Thread(
                target=lambda: self.app.run(port=self.port, host="0.0.0.0", debug=True, use_reloader=False)).start()

    # set partition leader if it does not exist
    def set_partition_leader(self, app):
        self.app = app  # define flask app
        while True:
            # in case no partition leader
            self.lock.acquire()
            if not self.partition_leader_exists:
                self.lock.release()
                # send data to se partition leader
                leader_data = {'port': self.udp_port, 'leader': self.leader_value}
                for destination_port in self.ports_to_send:
                    self.send_data(leader_data, destination_port)
            else:
                self.lock.release()
            sleep(2)
