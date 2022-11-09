import socket
import logging

from config import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


class ServerCommunication:
    def send_data(self, data, udp_to_send):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        prepared_data = str.encode(data)
        sock.sendto(prepared_data, (ip, udp_to_send))
        logging.info('Sending UDP package to another server...')

    def receive_data(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, udp_port))
        while True:
            data, address = sock.recvfrom(buffer_size)
            logging.info(f'Receiving UDP package from another server...')
            logging.info(f'Received: {data}')
