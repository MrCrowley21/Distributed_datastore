from flask import Flask, request, jsonify
from flask_sock import Sock
import requests

from Components_logic.server_communication import *

# initialize the logger mode
logging.basicConfig(level=logging.DEBUG)

# initialize the server (app)
app = Flask(__name__)
web_socket = Sock(app)
server_communication = ServerCommunication()


# http communication with clients
@app.route('/', methods=['POST', 'PUT', 'GET', 'DELETE'])
def receive_client_request():
    choices = [i % 10 for i in server_communication.active_services]
    choices.append(server_communication.server_id - 1)
    responsible_server = random.choice(choices)
    if responsible_server != server_communication.server_id:
        address = server_communication.addresses[str(responsible_server)]

    if request.method == 'POST':
        received_data = request.json
        if server_communication.is_partition_leader and server_communication.server_id != responsible_server:
            requests.post(address, json=received_data)
            return jsonify(received_data)
        logging.info(f'Receiving new data...')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, received_data,
                                                                            server_communication.tcp_port)).start()
        return jsonify(received_data)
    elif request.method == 'PUT':
        requested_data = request.json
        if server_communication.is_partition_leader and server_communication.server_id != responsible_server:
            requests.put(address, json=requested_data)
            return jsonify(requested_data)
        logging.info(f'Updating existing data...')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, requested_data,
                                                                            server_communication.tcp_port)).start()
        return jsonify(requested_data)
    elif request.method == 'GET':
        requested_key = request.json
        if server_communication.is_partition_leader and server_communication.server_id != responsible_server:
            response = requests.get(address, json=requested_key).json()
            return jsonify(response)
        logging.info(f'Some data has been requested')
        requested_data = server_communication.distribute_data(request.method, requested_key, server_communication.
                                                              tcp_port)
        return jsonify(requested_data)
    elif request.method == 'DELETE':
        data_to_delete = request.json
        if server_communication.is_partition_leader and server_communication.server_id != responsible_server:
            response = requests.delete(address, json=data_to_delete).json()
            return jsonify(response)
        logging.info(f'Some data requested to be deleted')
        threading.Thread(target=server_communication.distribute_data, args=(request.method, data_to_delete,
                                                                            server_communication.tcp_port)).start()
        return jsonify(data_to_delete)


@web_socket.route('/report')
def get_report(ws):
    while True:
        user_request = ws.receive()
        logging.info(f'Request via websocket was received')
        user_report_name = server_communication.create_user_report()
        with open('user_data.txt', 'wb') as local_file:
           user_report = server_communication.ftp.retrbinary(f'RETR {user_report_name}', local_file.write)
        ws.send(user_report)


# initiate server
if __name__ == "__main__":
    # set partition leader
    threading.Thread(target=server_communication.receive_tcp_data).start()
    # delay allowing receiver establish connection
    sleep(0.7)
    threading.Thread(target=server_communication.set_partition_leader, args=(app,)).start()
    threading.Thread(target=server_communication.receive_udp_data).start()
    threading.Thread(target=server_communication.start_synchronisation).start()
    threading.Thread(target=lambda: app.run(port=server_communication.port, host="0.0.0.0",
                                            debug=True, use_reloader=False)).start()

