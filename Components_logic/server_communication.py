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
from Components_logic.storage import Storage

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


# class that defines communication of servers
class ServerCommunication:
    def __init__(self):
        self.app = None  # flask app
        self.storage = Storage()
        self.leader_value = random.randint(0, 100)  # the value to determine the leader
        self.leader_data = {}  # the leader received messages
        self.is_partition_leader = False  # the state if is leader partition
        self.partition_leader_exists = False  # the state if partition leader exists
        self.candidates_id = []  # the ids of the candidates
        self.active_services = []  # list of active services
        self.heartbeat = 2  # define the heartbeat of the server
        self.partition_leader_checked = True  # define if partition leader was checked
        self.server_id, self.address, self.state, self.port, self.udp_port, self.tcp_port, self.buffer_size, \
            self.udp_ports_to_send, self.tcp_ports_to_send = Config().extract_data()
        self.data_location = {}
        self.lock = Lock()

    # send data through UDP
    def send_udp_data(self, data, udp_to_send):
        # initiate UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.connect((self.address, self.port))
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # encode data
        prepared_data = dumps(data).encode('utf-8')
        # send data
        try:
            udp_socket.sendto(prepared_data, (self.address, udp_to_send))
            logging.info(f'Sending UDP package to another server... port: {udp_to_send}')
        except:
            pass

    # receive data through UDP
    def receive_udp_data(self):
        # initiate UDP socket
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # hostname = socket.gethostname()
        # self.address = socket.gethostbyname(hostname)[:-1] + '1'
        udp_socket.bind(('', self.udp_port))
        # always receiving
        while True:
            logging.info(f'Setting up the socket to receive data...')
            # receive and decode data
            data, address = udp_socket.recvfrom(self.buffer_size)
            data = loads(data.decode('utf-8'))
            # if information about leader
            logging.info(f'Receiving UDP package from another server...')
            logging.info(f'Received: {data}')
            try:
                port = data["port"]
                method = data["method"]
                data_store_data = data["data"]
                self.resolve_request(method, data_store_data, port)
            #  if any other data sent through UDP
            except:
                logging.info(f'Something went wrong...')

    def distribute_data(self, method, data, port):
        if method == 'POST':
            try:
                key = data["key"]
                self.data_location[key] = []
                to_post = random.sample(self.active_services, len(self.tcp_ports_to_send) // 2 + 1)
                for port in to_post:
                    self.data_location[key].append(port)
                    if port != self.tcp_port:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.storage.create_data(data)
            except:
                logging.info(f'Something went wrong')
        elif method == 'PUT':
            try:
                key = data["key"]
                for port in self.data_location[key]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.storage.update_data(data)
            except:
                logging.info(f'Something went wrong')
        elif method == 'DELETE':
            try:
                key = data["key"]
                for port in self.data_location[key]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.storage.delete_data(data)
            except:
                logging.info(f'Something went wrong')
        elif method == 'GET':
            try:
                key = data["key"]
                for port in self.data_location[key]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                    else:
                        return self.storage.get_data(data)
                    break
            except:
                logging.info(f'Something went wrong')

    def resolve_request(self, method, data, port):
        if method == 'POST':
            self.storage.create_data(data)
        elif method == 'PUT':
            self.storage.update_data(data)
        elif method == 'DELETE':
            self.storage.delete_data(data)
        elif method == 'GET':
            data_to_send = self.storage.get_data(data)
            self.establish_tcp_connection(data_to_send, port)

    def establish_tcp_connection(self, data, tcp_port):
        logging.info(f'Trying to establish TCP connection')
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.address == '':
            hostname = socket.gethostname()
            self.address = socket.gethostbyname(hostname)[:-1] + '1'
        try:
            tcp_socket.connect((self.address, tcp_port))
            # tcp_socket.listen()
            # conn, addr = tcp_socket.accept()
            logging.info(f'Data sent over TCP')
            data = dumps(data).encode('utf-8')
            tcp_socket.sendall(data)
            tcp_socket.close()
            self.lock.acquire()
            self.active_services.append(tcp_port)
            self.lock.release()
        except:
            logging.info(f'Something went wrong')

    def receive_tcp_data(self):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind(('', self.tcp_port))
        tcp_socket.listen(5)
        while True:
            conn, addr = tcp_socket.accept()
            with conn:
                logging.info(f'Connected by {addr}')
                while True:
                    data = conn.recv(self.buffer_size)
                    if not data:
                        break
                    data = loads(data.decode('utf-8'))
                    threading.Thread(target=self.check_received_tcp_data, args=(data,)).start()
                    logging.info(f'TCP packet received. Data: {data}')
                conn.close()

    def check_received_tcp_data(self, data):
        logging.info('Distributing the data')
        if 'candidate_id' in data:
            self.lock.acquire()
            self.candidates_id.append(data['candidate_id'])
            self.lock.release()
            if len(self.candidates_id) == len(self.tcp_ports_to_send) and not self.partition_leader_exists:
                threading.Thread(target=self.find_partition_leader).start()
        elif 'leader' in data:
            self.partition_leader_exists = True
        self.partition_leader_checked = True

    # find the partition leader if exist or set the existing one
    def find_partition_leader(self):
        # compute value to set the partition leader (random)
        logging.info(f'Trying to set partition leader')
        self.candidates_id.append(self.server_id)
        self.candidates_id.sort()
        logging.info(f'{self.candidates_id[-1] == self.server_id}, {self.partition_leader_exists}')
        self.lock.acquire()
        if self.candidates_id[-1] == self.server_id and not self.partition_leader_exists:
            self.lock.release()
            for server_port in self.tcp_ports_to_send:
                threading.Thread(target=self.establish_tcp_connection, args=({"leader": True}, server_port)).start()
                # self.establish_tcp_connection({"leader": True}, server_port)
            self.is_partition_leader = True
            self.partition_leader_exists = True
            logging.info(f'Partition leader address: http://127.0.0.1:' + str(self.port) + '/')
            # initiate flask app and HTTP requests
            threading.Thread(
                target=lambda: self.app.run(port=self.port, host="0.0.0.0", debug=True, use_reloader=False)).start()
        else:
            self.lock.release()
        self.candidates_id.clear()

    # set partition leader if it does not exist
    def set_partition_leader(self, app):
        self.app = app  # define flask app
        while True:
            # in case no partition leader
            self.lock.acquire()
            if not self.partition_leader_exists:
                self.lock.release()
                # send data to se partition leader
                leader_data = {'candidate_id': self.server_id}
                for destination_port in self.tcp_ports_to_send:
                    self.establish_tcp_connection(leader_data, destination_port)
            elif self.partition_leader_exists and self.is_partition_leader:
                self.lock.release()
                self.active_services.clear()
                self.active_services.append(self.tcp_port)
                for destination_port in self.tcp_ports_to_send:
                    threading.Thread(target=self.establish_tcp_connection, args=({}, destination_port)).start()
            elif self.partition_leader_exists and not self.is_partition_leader:
                if not self.partition_leader_checked:
                    self.lock.release()
                    self.partition_leader_exists = False
                else:
                    self.lock.release()
                self.partition_leader_checked = False
            else:
                self.lock.release()
            sleep(self.heartbeat)
