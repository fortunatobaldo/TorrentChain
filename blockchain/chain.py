class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.pending_transactions = []

    def create_genesis_block(self):
        return Block(0, [], "0")

    def add_block(self, block):
        if self.is_valid_block(block):
            self.chain.append(block)
            self.pending_transactions = []
            return True
        return False

    def is_valid_block(self, block):
        previous_block = self.chain[-1]
        return block.previous_hash == previous_block.hash and block.hash == block.calculate_hash()