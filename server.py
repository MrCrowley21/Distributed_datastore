from flask import Flask, request, jsonify

from Components_logic.server_communication import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)

# initialize the server (app)
app = Flask(__name__)
server_communication = ServerCommunication()


# http communication with clients
@app.route('/', methods=['POST', 'PUT', 'GET', 'DELETE'])
def receive_client_request():
    if request.method == 'POST':
        received_data = request.json
        logging.info(f'Receiving new data...')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, received_data,
                                                                            server_communication.tcp_port)).start()
        return jsonify(received_data)
    elif request.method == 'PUT':
        requested_data = request.json
        logging.info(f'Updating existing data...')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, requested_data,
                                                                            server_communication.tcp_port)).start()
        return jsonify(requested_data)
    elif request.method == 'GET':
        requested_key = request.json
        logging.info(f'Some data has been requested')
        requested_data = server_communication.distribute_data(request.method, requested_key, server_communication.tcp_port).start()
        return requested_data
    elif request.method == 'DELETE':
        data_to_delete = request.json
        logging.info(f'Some data requested to be deleted')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, data_to_delete,
                                                                            server_communication.tcp_port)).start()
        return 'Requested data has been deleted'


# initiate server
if __name__ == "__main__":
    # initiate data receiving
    # threading.Thread(target=server_communication.receive_udp_data, args=(storage,)).start()
    # set partition leader
    threading.Thread(target=server_communication.receive_tcp_data).start()
    # delay allowing receiver establish connection
    sleep(0.5)
    threading.Thread(target=server_communication.set_partition_leader, args=(app,)).start()
    threading.Thread(target=server_communication.receive_udp_data).start()

