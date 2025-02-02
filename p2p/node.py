import socket
import threading

class Node:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.peers = []  # Peers address (host, port)
        self.storage = {}  # Storaged chunks (chunk_hash, chunk_data)    

    def start(self):
        server = threading.Thread(target=self.run_server)
        server.start()

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_connection, args=(conn, addr)).start()

    def handle_connection(self, conn, addr):
        # Todo: Connection handling logic
        pass

    def connect_to_peer(self, peer_host, peer_port):
        # ToDo: Connect to peer
        pass