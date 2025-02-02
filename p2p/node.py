import socket
import threading

class Node:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.peers = []  # Lista de peers (endereços IP:Porta)
        self.storage = {}  # Chunks armazenados (hash: dados)

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
        # Lógica para receber chunks e gerenciar peers
        pass

    def connect_to_peer(self, peer_host, peer_port):
        # Lógica para conectar a outro peer
        pass