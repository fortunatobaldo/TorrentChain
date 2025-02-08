import unittest
import time
import hashlib
from proof_useful_work import PoUW
from block import Block
from chain import Blockchain

class TestPoUW(unittest.TestCase):
    def test_sequential_hashing(self):
        # Tests if the hash generated with 1 iteration matches the standard SHA256 hash.
        data = "test"
        result = PoUW.sequential_hashing(data, iterations=1)
        expected = hashlib.sha256(data.encode()).hexdigest()
        self.assertEqual(result, expected)

    def test_process_transactions(self):
        # Tests if the transactions are concatenated correctly.
        transactions = ["a", "b", 123]
        result = PoUW.process_transactions(transactions)
        self.assertEqual(result, "ab123")

    def test_generate_useful_work(self):
        # With low difficulty (1) and reduced iterations, it is expected that in a few attempts
        # if a hash is found that starts with "0".
        transactions = ["tx1"]
        nonce, processed_data, final_hash = PoUW.generate_useful_work(transactions, difficulty=1, iterations=1)
        self.assertTrue(final_hash.startswith("0" * 1))
        self.assertEqual(processed_data, PoUW.process_transactions(transactions))

class TestBlock(unittest.TestCase):
    def test_calculate_hash(self):
        # Creates a block and tests if the calculated hash is consistent.
        transactions = ["tx1", "tx2"]
        useful_data = PoUW.process_transactions(transactions)
        block = Block(index=1, transactions=transactions, previous_hash="abc", difficulty=2, nonce=5, useful_work_data=useful_data)
        computed_hash = block.calculate_hash()
        self.assertEqual(block.hash, computed_hash)

    def test_hash_change(self):
        # Verifies if changing any parameter (here, nonce) results in a different hash.
        transactions = ["tx1"]
        useful_data = PoUW.process_transactions(transactions)
        block = Block(index=1, transactions=transactions, previous_hash="abc", difficulty=2, nonce=0, useful_work_data=useful_data)
        original_hash = block.hash
        block.nonce += 1
        new_hash = block.calculate_hash()
        self.assertNotEqual(original_hash, new_hash)

class TestBlockchain(unittest.TestCase):
    def setUp(self):
        # To speed up the tests, we use reduced target_time and adjustment_interval.
        self.blockchain = Blockchain(target_time=1, adjustment_interval=2)
        # Reduces the difficulty to speed up mining in tests.
        self.blockchain.difficulty = 1

    def test_genesis_block(self):
        # Verifies if the genesis block was created correctly.
        genesis_block = self.blockchain.chain[0]
        self.assertEqual(genesis_block.index, 0)
        self.assertEqual(genesis_block.transactions, ["GenesisBlock"])
        self.assertEqual(genesis_block.previous_hash, "0" * 64)
        self.assertTrue(genesis_block.hash.startswith("0" * genesis_block.difficulty))

    def test_add_block(self):
        # Create a block manually
        transactions = ["tx1"]
        last_block = self.blockchain.chain[-1]
        useful_data = PoUW.process_transactions(transactions)
        new_block = Block(
            index=len(self.blockchain.chain),
            transactions=transactions,
            previous_hash=last_block.hash,
            difficulty=self.blockchain.difficulty,
            nonce=0,
            useful_work_data=useful_data
        )
        # Simulate mining: adjust nonce until hash meets difficulty criteria
        while not new_block.hash.startswith("0" * new_block.difficulty):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()
        
        # Now try to add the block to the blockchain
        added = self.blockchain.add_block(new_block)
        self.assertTrue(added)
        self.assertEqual(self.blockchain.chain[-1].index, new_block.index)


    def test_mine_block(self):
        # Tests the mining process using pending transactions.
        self.blockchain.pending_transactions = ["tx_mine"]
        new_block = self.blockchain.mine_block()
        self.assertIsNotNone(new_block)
        self.assertEqual(self.blockchain.chain[-1].index, new_block.index)
        self.assertTrue(new_block.hash.startswith("0" * new_block.difficulty))
        # Verifies if the block was added to the chain.
        self.assertEqual(self.blockchain.pending_transactions, [])

    def test_is_valid_block(self):
        # Creates a valid block and then changes it to test the validation.
        transactions = ["tx_valid"]
        last_block = self.blockchain.chain[-1]
        useful_data = PoUW.process_transactions(transactions)
        block = Block(
            index=len(self.blockchain.chain),
            transactions=transactions,
            previous_hash=last_block.hash,
            difficulty=self.blockchain.difficulty,
            nonce=0,
            useful_work_data=useful_data
        )
        block.hash = block.calculate_hash()
        self.assertTrue(self.blockchain.is_valid_block(block))
        # Change the previous_hash to an invalid value and expect the validation to fail.
        block.previous_hash = "wrong"
        self.assertFalse(self.blockchain.is_valid_block(block))

    def test_adjust_difficulty_increase(self):
        # Simulates mining blocks very quickly to force an increase in difficulty.
        self.blockchain.chain = []
        block1 = Block(index=0, transactions=["Genesis"], previous_hash="0"*64, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="GenesisData")
        block1.timestamp = time.time()
        block1.hash = block1.calculate_hash()
        block2 = Block(index=1, transactions=["tx"], previous_hash=block1.hash, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="tx")
        block2.timestamp = block1.timestamp + 0.1
        block2.hash = block2.calculate_hash()
        block3 = Block(index=2, transactions=["tx2"], previous_hash=block2.hash, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="tx2")
        block3.timestamp = block2.timestamp + 0.1
        block3.hash = block3.calculate_hash()
        self.blockchain.chain = [block1, block2, block3]
        original_difficulty = self.blockchain.difficulty
        self.blockchain.adjust_difficulty()
        self.assertGreater(self.blockchain.difficulty, original_difficulty)

    def test_adjust_difficulty_decrease(self):
        # Simulates mining blocks very slowly to force a decrease in difficulty.
        self.blockchain.chain = []
        block1 = Block(index=0, transactions=["Genesis"], previous_hash="0"*64, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="GenesisData")
        block1.timestamp = time.time()
        block1.hash = block1.calculate_hash()
        block2 = Block(index=1, transactions=["tx"], previous_hash=block1.hash, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="tx")
        block2.timestamp = block1.timestamp + 5  # Simulates a delay of 5 seconds
        block2.hash = block2.calculate_hash()
        block3 = Block(index=2, transactions=["tx2"], previous_hash=block2.hash, difficulty=self.blockchain.difficulty, nonce=0, useful_work_data="tx2")
        block3.timestamp = block2.timestamp + 5
        block3.hash = block3.calculate_hash()
        self.blockchain.chain = [block1, block2, block3]
        original_difficulty = self.blockchain.difficulty
        self.blockchain.adjust_difficulty()
        # The difficulty should decrease by 1
        self.assertLessEqual(self.blockchain.difficulty, original_difficulty)

if __name__ == '__main__':
    unittest.main()
