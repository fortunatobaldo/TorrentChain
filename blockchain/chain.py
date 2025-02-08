from proof_useful_work import PoUW
from block import Block

class Blockchain:
    def __init__(self, target_time=60, adjustment_interval=10):
        self.difficulty = 4  # Initial difficulty
        self.target_time = target_time
        self.adjustment_interval = adjustment_interval
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []

    def create_genesis_block(self):
        """
        Creates and mines the genesis block, ensuring that its hash meets the difficulty requirement.
        """
        genesis_transactions = ["GenesisBlock"]
        useful_data = PoUW.process_transactions(genesis_transactions)
        block = Block(
            index=0,
            transactions=genesis_transactions,
            previous_hash="0" * 64,
            difficulty=self.difficulty,
            nonce=0,
            useful_work_data=useful_data
        )
        # Mine the block: adjust the nonce until the hash meets the difficulty requirement.
        while not block.hash.startswith("0" * block.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()
        return block

    def add_block(self, block):
        """
        Adds the block to the chain if it is valid.
        After adding, adjusts the difficulty if needed.
        """
        if self.is_valid_block(block):
            self.chain.append(block)
            if block.index != 0 and block.index % self.adjustment_interval == 0:
                self.adjust_difficulty()
            return True
        return False

    def mine_block(self):
        """
        Mines a new block using the pending transactions.
        Generates a new block and adjusts the nonce until the hash meets the difficulty requirement.
        """
        if not self.pending_transactions:
            return None

        last_block = self.chain[-1]
        useful_data = PoUW.process_transactions(self.pending_transactions)
        new_block = Block(
            index=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=last_block.hash,
            difficulty=self.difficulty,
            nonce=0,
            useful_work_data=useful_data
        )
        # Mine the block by iterating the nonce until the hash meets the difficulty criteria.
        while not new_block.hash.startswith("0" * new_block.difficulty):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()
        if self.add_block(new_block):
            self.pending_transactions = []
            return new_block
        return None

    def is_valid_block(self, block):
        """
        Validates the block by checking:
         - If the previous_hash of the block matches the hash of the last block in the chain.
         - If the recalculated hash equals the stored hash.
         - If the hash meets the difficulty criteria.
         - If the useful work data matches the processed transactions.
        """
        last_block = self.chain[-1]
        if block.previous_hash != last_block.hash:
            print("Invalid previous hash")
            return False
        if block.hash != block.calculate_hash():
            print("Hash recalculation does not match")
            return False
        if not block.hash.startswith("0" * block.difficulty):
            print("Hash does not meet difficulty requirement")
            return False
        if block.useful_work_data != PoUW.process_transactions(block.transactions):
            print("Useful work data is invalid")
            return False
        return True

    def adjust_difficulty(self):
        """
        Adjusts the mining difficulty based on the time elapsed for mining the recent blocks.
        """
        if len(self.chain) <= self.adjustment_interval:
            return

        last_adjustment_block = self.chain[-self.adjustment_interval - 1]
        latest_block = self.chain[-1]
        actual_time = latest_block.timestamp - last_adjustment_block.timestamp
        expected_time = self.target_time * self.adjustment_interval

        print(f"\nAdjusting difficulty: {self.adjustment_interval} blocks in {actual_time:.2f}s (expected: {expected_time}s)")
        if actual_time < expected_time / 2:
            self.difficulty += 1
            print("Increasing difficulty to", self.difficulty)
        elif actual_time > expected_time * 2:
            self.difficulty = max(1, self.difficulty - 1)
            print("Decreasing difficulty to", self.difficulty)
        else:
            print("Difficulty remains at", self.difficulty)
