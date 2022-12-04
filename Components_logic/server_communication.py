import socket
import logging
import random
import threading
from io import BytesIO
from threading import Lock
from time import sleep
from copy import deepcopy
import json
from json import load, loads, dumps
import tempfile
from ftplib import FTP

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
        self.heartbeat = 3  # define the heartbeat of the server
        self.partition_leader_checked = True  # define if partition leader was checked
        self.server_id, self.address, self.state, self.port, self.udp_port, self.tcp_port, self.buffer_size, \
        self.udp_ports_to_send, self.tcp_ports_to_send, self.addresses = Config().extract_data()
        self.get_data = {}  # the data gotten by a server
        self.data_location = {}  # the location of the data
        self.lock = Lock()  # locking mechanism
        self.server_registrations = [[i, 0] for i in
                                     self.tcp_ports_to_send]  # the number of registrations contained in each server
        self.server_registrations.append([self.tcp_port, 0])
        self.used_keys = []  # list of keys that are not available
        self.ftp = FTP('ftp.us.debian.org')
        self.ftp.login()
        self.ftp.cwd('debian')

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
                self.resolve_request(data)
            #  if any other data sent through UDP
            except:
                logging.info(f'UDP receive Something went wrong...')

    # Dual Writes
    def distribute_data(self, method, data, port):
        data["port"] = self.tcp_port
        if method == 'POST':
            try:
                data["method"] = 'POST'
                key = data["key"]
                self.used_keys.append(key)
                self.data_location[str(key)] = []
                self.server_registrations.sort(key=lambda x: x[1])
                to_post = []
                for j in range(len(self.tcp_ports_to_send) // 2 + 1):
                    to_post.append(self.server_registrations[j][0])
                    self.server_registrations[j][1] += 1
                for port in to_post:
                    self.data_location[str(key)].append(port)
                    if port != self.tcp_port:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.storage.create_data(data)
            except:
                logging.info(f'Something went wrong')
        elif method == 'PUT':
            try:
                data["method"] = 'PUT'
                key = data["key"]
                for port in self.data_location[str(key)]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.storage.update_data(data)
            except:
                logging.info(f'Distribution PUT Something went wrong')
        elif method == 'DELETE':
            try:
                data["method"] = 'DELETE'
                key = data["key"]
                for port in self.data_location[str(key)]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                    else:
                        self.lock.acquire()
                        self.storage.delete_data(data)
                        self.lock.release()
                self.used_keys.remove(key)
            except:
                logging.info(f'Distribution DELETE Something went wrong')
        elif method == 'GET':
            try:
                data["method"] = 'GET'
                key = data["key"]
                for port in self.data_location[str(key)]:
                    if port != self.tcp_port and self.tcp_port in self.active_services:
                        self.send_udp_data(data, port - 10)
                        while True:
                            if port in self.get_data:
                                gotten_data = self.get_data[port]
                                self.get_data.pop(port)
                                return gotten_data
                    else:
                        gotten_data = self.storage.get_data(data)
                        return gotten_data
            except:
                logging.info(f'Distribution Something went wrong')

    def resolve_request(self, data):
        self.lock.acquire()
        if data["method"] == 'POST':
            self.storage.create_data(data)
        elif data["method"] == 'PUT':
            self.storage.update_data(data)
        elif data["method"] == 'DELETE':
            self.storage.delete_data(data)
        elif data["method"] == 'GET':
            data_to_send = {}
            data_to_send["data"] = self.storage.get_data(data)
            data_to_send["port"] = self.tcp_port
            data_to_send["method"] = 'GET'
            self.establish_tcp_connection(data_to_send, data["port"])
        self.lock.release()
        logging.info(f'{self.tcp_port}, {self.storage.storage}')

    def establish_tcp_connection(self, data, tcp_port):
        logging.info(f'Trying to establish TCP connection')
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.address == '':
            hostname = socket.gethostname()
            self.address = socket.gethostbyname(hostname)[:-1] + '1'
        try:
            tcp_socket.connect((self.address, tcp_port))
            logging.info(f'Data sent over TCP')
            data = dumps(data).encode('utf-8')
            tcp_socket.sendall(data)
            tcp_socket.close()
            self.lock.acquire()
            self.active_services.append(tcp_port)
            self.lock.release()
        except:
            logging.info(f'TCP Something went wrong')

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
        logging.info(f'Distributing the data {data}')
        if 'candidate_id' in data:
            self.lock.acquire()
            self.candidates_id.append(data['candidate_id'])
            self.lock.release()
            if len(self.candidates_id) == len(self.tcp_ports_to_send) and not self.partition_leader_exists:
                threading.Thread(target=self.find_partition_leader).start()
        elif 'leader' in data:
            self.partition_leader_exists = True
        elif 'method' in data:
            self.get_data[data["port"]] = data["data"]
            logging.info(f'{data["port"], data["data"]}')
        elif "data_location" in data:
            self.lock.acquire()
            self.data_location.clear()
            self.data_location = deepcopy(data["data_location"])
            self.lock.release()
        elif "sync" in data:
            logging.info(f'Sending data for synchronization...')
            for port in self.tcp_ports_to_send:
                to_send = {"port": self.tcp_port, "storage": self.storage.storage}
                self.establish_tcp_connection(to_send, port)
        elif "storage" in data:
            logging.info(f'Receiving data for synchronization...')
            threading.Thread(target=self.synchronize_data, args=(data,)).start()
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
                    self.partition_leader_exists = True
                    self.lock.release()
                self.partition_leader_checked = False
            else:
                self.lock.release()
            sleep(self.heartbeat)

    def start_synchronisation(self):
        while True:
            sleep(self.heartbeat * 5)
            self.lock.acquire()
            if self.is_partition_leader:
                logging.info(f'Starting synchronization...')
                self.lock.release()
                self.synchronize_data_location()
                for port in self.tcp_ports_to_send:
                    data = {"sync": True, "port": self.tcp_port, "storage": self.storage.storage}
                    self.establish_tcp_connection(data, port)
            else:
                self.lock.release()

    def synchronize_data_location(self):
        for port in self.tcp_ports_to_send:
            data = {"data_location": self.data_location}
            threading.Thread(target=self.establish_tcp_connection, args=(data, port)).start()

    def synchronize_data(self, data):
        port = data["port"]
        received_data = data["storage"]
        for key in self.data_location:
            logging.info(f'Synchronizing data...')
            if port in self.data_location[key] and self.tcp_port in self.data_location[key] and port in self.used_keys:
                self.lock.acquire()
                if received_data[key]["time"] > self.storage.storage[int(key)]["time"]:
                    self.storage.storage[int(key)].clear()
                    self.storage.storage[int(key)] = deepcopy(received_data[key])
                    self.lock.release()
                elif key not in received_data and int(key) in self.storage.storage:
                    self.storage.storage.pop(int(key))
                    self.lock.release()
                else:
                    self.lock.release()

    def create_user_report(self):
        temp_file = tempfile.NamedTemporaryFile(mode='w+')
        with temp_file:
            self.lock.acquire()
            json.dump(self.storage.storage, temp_file)
            temp_file.flush()
            self.lock.release()
            temp_file.seek(0)
            data = temp_file.read()
            self.ftp.storbinary(f'STOR {temp_file.name}', data)
        return temp_file.name
