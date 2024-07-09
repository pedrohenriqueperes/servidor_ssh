import paramiko
import uuid
import threading
import socket

class SSHManager:
    def __init__(self):
        self.connections = {}
        self.listeners = {}
        self.lock = threading.Lock()

    def add_connection(self, host, username, password):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password)
        connection_id = str(uuid.uuid4())
        with self.lock:
            self.connections[connection_id] = client
        return connection_id

    def remove_connection(self, connection_id):
        with self.lock:
            if connection_id in self.connections:
                self.connections[connection_id].close()
                del self.connections[connection_id]

    def execute_command(self, connection_id, command):
        with self.lock:
            if connection_id in self.connections:
                stdin, stdout, stderr = self.connections[connection_id].exec_command(command)
                return stdout.read().decode(), stderr.read().decode()
            else:
                return None, "Connection not found"

    def get_connections(self):
        with self.lock:
            return self.connections

    def add_listener(self, host, port, username, password):
        listener_id = str(uuid.uuid4())
        thread = threading.Thread(target=self._listener_thread, args=(listener_id, host, port, username, password))
        thread.start()
        with self.lock:
            self.listeners[listener_id] = thread
        return listener_id

    def remove_listener(self, listener_id):
        with self.lock:
            if listener_id in self.listeners:
                # Não há uma maneira direta de parar um thread em Python
                # Você precisa lidar com isso adequadamente dentro do thread
                del self.listeners[listener_id]

    def _listener_thread(self, listener_id, host, port, username, password):
        server = paramiko.SSHServer()
        server.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        class Server(paramiko.ServerInterface):
            def __init__(self):
                self.event = threading.Event()

            def check_auth_password(self, username_input, password_input):
                if username_input == username and password_input == password:
                    return paramiko.AUTH_SUCCESSFUL
                return paramiko.AUTH_FAILED

            def get_allowed_auths(self, username):
                return 'password'

            def check_channel_request(self, kind, chanid):
                if kind == 'session':
                    return paramiko.OPEN_SUCCEEDED
                return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(100)
            while True:
                client, addr = sock.accept()
                transport = paramiko.Transport(client)
                transport.add_server_key(paramiko.RSAKey(filename='test_rsa.key'))
                server_instance = Server()
                try:
                    transport.start_server(server=server_instance)
                    chan = transport.accept(20)
                    if chan is None:
                        continue
                    connection_id = str(uuid.uuid4())
                    with self.lock:
                        self.connections[connection_id] = chan
                    while True:
                        if chan.recv_ready():
                            output = chan.recv(1024).decode('utf-8')
                            print(output)  # You might want to send this to a logging system or the main application
                except Exception as e:
                    print(f"Error: {e}")
                finally:
                    transport.close()
        except Exception as e:
            print(f"Listener error: {e}")

    def get_listeners(self):
        with self.lock:
            return self.listeners
