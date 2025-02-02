import hashlib

class PoUW:
    @staticmethod
    def generate_useful_work(data):
        # Simple Proof of Useful Work Algorithm
        nonce = 0
        while True:
            hash_attempt = hashlib.sha256(f"{data}{nonce}".encode()).hexdigest()
            if hash_attempt.startswith("0000"):
                return nonce, hash_attempt
            nonce += 1