import time
from proof_useful_work import PoUW  # Import the PoUW module

class Block:
    def __init__(self, index, transactions, previous_hash, difficulty, nonce=0, useful_work_data=None):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.useful_work_data = useful_work_data  # Processed data
        self.difficulty = difficulty             # Difficulty applied to this block
        self.hash = self.calculate_hash()

    def calculate_hash(self, iterations=1000):
        """
        Calculates the block hash by combining its attributes, using the sequential hashing
        function from PoUW.
        """
        block_data = (
            str(self.index) +
            str(self.timestamp) +
            str(self.transactions) +
            str(self.previous_hash) +
            str(self.nonce) +
            str(self.useful_work_data) +
            str(self.difficulty)
        )
        return PoUW.sequential_hashing(block_data, iterations)
