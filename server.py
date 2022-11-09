import threading
import logging
import socket
from time import sleep
from flask import Flask, request, jsonify

from config import *
from Components_logic.server_communication import *
from Components_logic.storage import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)

# initialize the server (app)
app = Flask(__name__)
server_communication = ServerCommunication()
storage = Storage()


@app.route('/', methods=['POST', 'GET', 'DELETE'])
def receive_client_request():
    if request.method == 'POST':
        received_data = request.json
        logging.info(f'Receiving new data to create or update')
        threading.Thread(target=storage.create_update_data, args=(received_data,)).start()
        return jsonify(received_data)
    elif request.method == 'GET':
        requested_key = request.json
        logging.info(f'Some data has been requested')
        requested_data = storage.get_data(requested_key['key'])
        return requested_data
    elif request.method == 'DELETE':
        data_to_delete = request.json
        logging.info(f'Some data requested to be deleted')
        threading.Thread(target=storage.delete_data, args=(data_to_delete['key'],)).start()
        return 'Requested data has been deleted'


if __name__ == "__main__":
    threading.Thread(target=server_communication.set_partition_leader, args=(app,)).start()
    threading.Thread(target=server_communication.receive_data, args=(storage,)).start()
    # threading.Thread(target=server_communication.set_partition_leader, args=(app,)).start()
    # threading.Thread(target=lambda: app.run(port=port, host="0.0.0.0", debug=True, use_reloader=False)).start()
    # while True:
    #     data = input()
    #     server_communication.send_data(data, 5000)
