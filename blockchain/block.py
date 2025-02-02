import hashlib
import time

class Block:
    def __init__(self, index, transactions, previous_hash, nonce=0):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions  # Lista de hashes de chunks
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.useful_work_data = None  # Dados do trabalho útil (ex.: hash de um resultado)
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_data = str(self.index) + str(self.timestamp) + str(self.transactions) + str(self.previous_hash) + str(self.nonce)
        return hashlib.sha256(block_data.encode()).hexdigest()