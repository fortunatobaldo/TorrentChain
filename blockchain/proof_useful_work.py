import hashlib

class PoUW:
    @staticmethod
    def sequential_hashing(data, iterations=1000):
        """
        Performs sequential hashing by repeatedly applying SHA256.
        """
        current_hash = data.encode()
        for _ in range(iterations):
            current_hash = hashlib.sha256(current_hash).digest()
        return current_hash.hex()

    @staticmethod
    def process_transactions(transactions):
        """
        Processes transactions by concatenating their string representations.
        """
        return "".join(str(tx) for tx in transactions)

    @staticmethod
    def generate_useful_work(transactions, difficulty=4, iterations=1000):
        """
        Performs useful work (Proof of Useful Work) by searching for a nonce such that
        the hash (after sequential hashing) starts with a number of zeros defined by the difficulty.
        """
        processed_data = PoUW.process_transactions(transactions)
        nonce = 0
        prefix = "0" * difficulty
        while True:
            candidate = f"{processed_data}{nonce}"
            final_hash = PoUW.sequential_hashing(candidate, iterations)
            if final_hash.startswith(prefix):
                return nonce, processed_data, final_hash
            nonce += 1
