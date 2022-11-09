import logging
import threading

from Components_logic.server_communication import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


# clas o define local storage
class Storage:
    def __init__(self):
        self.storage = {}  # the actual storage

    # create or update data request
    def create_update_data(self, data):
        # commit modifications
        key = data['key']
        self.storage[key] = data['data']
        logging.info(f'New data has been updated/created. Current stored data:\n{self.storage}')
        # send modifications to all partitions
        for destination_port in ports_to_send:
            threading.Thread(target=ServerCommunication().send_data, args=(self.storage, destination_port)).start()

    # get data request
    def get_data(self, key):
        # in ase data exists
        try:
            logging.info(f'Giving data to user...')
            return self.storage[key]
        # in case no such data
        except KeyError:
            logging.info('Not such data registered')
            return 'No data'

    # delete data request
    def delete_data(self, key):
        # in case data exists
        try:
            # delete requested data
            del self.storage[key]
            logging.info(f'Data has been deleted. Current stored data:\n{self.storage}')
            # send modifications to all partitions
            for destination_port in ports_to_send:
                threading.Thread(target=ServerCommunication().send_data, args=(self.storage, destination_port)).start()
        # in case no such data
        except KeyError:
            logging.info('Nothing to delete')
            return 'Nothing to delete'
