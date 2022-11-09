import threading
import logging
import socket
from flask import Flask, request, jsonify

from config import *
from Components_logic.server_communication import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)

# initialize the server (app)
app = Flask(__name__)
server_communication = ServerCommunication()


@app.route('/', methods=['POST', 'GET', 'DELETE'])
def receive_client_request():
    if request.method == 'POST':
        data = request.json
        logging.info(f'Receiving new data to create or update')
        return jsonify(data)
    elif request.method == 'GET':
        data = request.json
        logging.info(f'Some data has been requested')
        return 'Some data send'
    elif request.method == 'DELETE':
        data = request.json
        logging.info(f'Some data requested to be deleted')
        return 'Deleted'


if __name__ == "__main__":
    # threading.Thread(target=lambda: app.run(port=8000, host="0.0.0.0", debug=True, use_reloader=False)).start()
    threading.Thread(target=server_communication.receive_data).start()
    while True:
        data = input()
        server_communication.send_data(data, 5000)
