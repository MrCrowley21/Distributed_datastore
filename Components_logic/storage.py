import logging
import threading


# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


# clas o define local storage
class Storage:
    def __init__(self):
        self.storage = {}  # the actual storage

    # create or update data request general schema
    def __create_update_data(self, data, logging_info):
        # commit modifications
        key = data['key']
        self.storage[key] = data['data']
        logging.info(f'{logging_info} Current stored data:\n{self.storage}')

    # create data in data storage
    def create_data(self, data):
        # commit modifications
        logging_info = 'New data has been created.'
        self.__create_update_data(data, logging_info)

    # update requested data in data storage
    def update_data(self, data):
        # commit modifications
        logging_info = 'The datastorage date has been updated.'
        self.__create_update_data(data, logging_info)

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
    def delete_data(self, data):
        # in case data exists
        try:
            key = data["key"]
            # delete requested data
            del self.storage[key]
            logging.info(f'Data has been deleted. Current stored data:\n{self.storage}')
        # in case no such data
        except KeyError:
            logging.info('Nothing to delete')
            return 'Nothing to delete'
