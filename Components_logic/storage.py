import logging
import threading

from Components_logic.server_communication import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


class Storage:
    def __init__(self):
        self.storage = {}

    def create_update_data(self, data):
        key = data['key']
        self.storage[key] = data['data']
        logging.info(f'New data has been updated/created. Current stored data:\n{self.storage}')
        for destination_port in ports_to_send:
            threading.Thread(target=ServerCommunication().send_data, args=(self.storage, destination_port)).start()

    def get_data(self, key):
        try:
            logging.info(f'Giving data to user...')
            return self.storage[key]
        except KeyError:
            logging.info('Not such data registered')
            return 'No data'

    def delete_data(self, key):
        try:
            del self.storage[key]
            logging.info(f'Data has been deleted. Current stored data:\n{self.storage}')
            for destination_port in ports_to_send:
                threading.Thread(target=ServerCommunication().send_data, args=(self.storage, destination_port)).start()
        except KeyError:
            logging.info('Nothing to delete')
            return 'Nothing to delete'
