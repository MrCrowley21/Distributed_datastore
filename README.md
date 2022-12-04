## Distributed Datastore
This repository, _Distributed Datastore_, represents the third laboratory work during 
the _Network Programming_ course. \
First, to run the project into a docker container, perform the following commands:
```` 
$ docker build -t server_image .  
$ docker compose up
````
The first line will create an image of our project, while the next one - run project inside 
a Docker Compose file. 
For the third checkpoint of this laboratory work there was proposed three main tasks:
* Data synchronization;
* Load balancing;
* WebSockets and FTP protocols usage.

As follows, it will be briefly described the implementation of the requirements specified above. \
In order to synchronize the data, it is used the Dual Write method, in other words, once data is
created, it is writen in all the specified locations it is supposed to be stored. To determine where
the data should be stored, it is kept the information about number of registration in each individual
server to add data in servers with minimal amount of stored data, in order to avoid the overflow of
one server while others have no requests at all. To avoid problems that may occur using this 
type of synchronization, once in a certain period of time, data from all servers are collected 
together and checked in the following way:
* Partition leader announce the daa synchronization process and send the information about the 
stored data to other servers in the cluster

````python
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
````

* After the server received information about starting synchronization, it sends its storage to 
every other active server in the cluster via TCP protocol and waits for a response from them.

````python
elif "sync" in data:
    logging.info(f'Sending data for synchronization...')
    for port in self.tcp_ports_to_send:
        to_send = {"port": self.tcp_port, "storage": self.storage.storage}
        self.establish_tcp_connection(to_send, port)
elif "storage" in data:
    logging.info(f'Receiving data for synchronization...')
    threading.Thread(target=self.synchronize_data, args=(data,)).start()
````

* In the end, it is checked the data that should be presented on the server with the data that is
actually presented. In case the received data is more up-to-date, the one from the storage is 
replaced, added in case it was added earlier or deleted, in case such an action occurred.

````python
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
````

The next task to discuss is load balancing. Basically, the issue is to avoid over partition
leader overloading. To solve this task, the HTTP is enabled for each server. When a request
reaches the partition leader, there is one active server chosen (counting the partition leader, as
well) to receive and deal with the received request.

````python
def receive_client_request():
    choices = [i % 10 for i in server_communication.active_services]
    choices.append(server_communication.server_id - 1)
    responsible_server = random.choice(choices)
    if responsible_server != server_communication.server_id:
        address = server_communication.addresses[str(responsible_server)]
````

The last but not the least implemented feature is WebSockets and FTP usage. It was decided to 
implement a simple model where the client sends a request via websockets and the current state of
the data storage is return in the form of a file. For Websockets it was used the extension of
Flask library, adapted to it, _flask-socket_'. For FTP, it was chosen to use _ftplib_. \
When a request via Websocket is intercept, the file itself is created.

````python
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
````

Then, it is extracted from the FTP server and send to the client who requested it.

````python
@web_socket.route('/report')
def get_report(ws):
    while True:
        user_request = ws.receive()
        logging.info(f'Request via websocket was received')
        user_report_name = server_communication.create_user_report()
        with open('user_data.txt', 'wb') as local_file:
           user_report = server_communication.ftp.retrbinary(f'RETR {user_report_name}', local_file.write)
        ws.send(user_report)
````