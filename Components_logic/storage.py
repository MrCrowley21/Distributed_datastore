import logging

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)


class Storage:
    def __init__(self):
        self.storage = {}

    def create_update_data(self, data):
        key = data['key']
        self.storage[key] = data['data']

    def get_data(self, key):
        try:
            return self.storage[key]
        except:
            logging.info('Not such data registered')

    def delete_data(self, key):
        try:
            del self.storage[key]
        except:
            logging.info('Nothing to delete')
