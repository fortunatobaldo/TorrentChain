import asyncio
import json
import logging
from hashlib import sha256
from struct import pack, unpack
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TorrentChainP2P")

class Node:
    def __init__(self, host: str, port: int, priv_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.host = host
        self.port = port
        self.priv_key = priv_key or ed25519.Ed25519PrivateKey.generate()
        self.pub_key = self.priv_key.public_key()
        
        # Network state
        self.peers: Dict[str, asyncio.StreamWriter] = {}  # "ip:port" -> StreamWriter
        self.chunks: Dict[str, bytes] = {}  # SHA256 hash -> chunk data
        self.lock = asyncio.Lock()
        
        # DHT
        self.routing_table: Dict[str, List[str]] = {}  # chunk hash -> list of peers

    async def start(self):
        server = await asyncio.start_server(
            self.handle_connection,
            self.host,
            self.port
        )
        logger.info(f"Node listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer_addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {peer_addr}")
        
        try:
            while True:
                # Message Protocol [4-byte length][message]
                raw_length = await reader.readexactly(4)
                msg_length = unpack('>I', raw_length)[0]
                raw_msg = await reader.readexactly(msg_length)
                
                message = await self.decode_message(raw_msg)
                await self.process_message(message, writer)
                
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.warning(f"Connection closed by {peer_addr}")
        finally:
            await self.remove_peer(writer)
            writer.close()

    async def connect_to_peer(self, host: str, port: int):
        peer_id = f"{host}:{port}"
        if peer_id in self.peers:
            return

        try:
            reader, writer = await asyncio.open_connection(host, port)
            logger.info(f"Connected to {peer_id}")
            
            # Initial Handshake 
            handshake = {
                "type": "handshake",
                "pub_key": self.pub_key.public_bytes_raw().hex(),
                "node_id": f"{self.host}:{self.port}"
            }
            await self.send_message(handshake, writer)
            
            # Adding peer to the list
            async with self.lock:
                self.peers[peer_id] = writer
                
            # Initial heartbeat
            asyncio.create_task(self.heartbeat(writer))
            
        except (ConnectionRefusedError, TimeoutError) as e:
            logger.error(f"Failed to connect to {peer_id}: {str(e)}")

    async def send_message(self, message: dict, writer: asyncio.StreamWriter):
        try:
            raw_msg = await self.encode_message(message)
            writer.write(pack('>I', len(raw_msg)) + raw_msg)
            await writer.drain()
        except ConnectionResetError:
            logger.warning("Connection lost while sending message")

    async def encode_message(self, message: dict) -> bytes:
        message["timestamp"] = asyncio.get_event_loop().time()
        raw_data = json.dumps(message).encode()
        signature = self.priv_key.sign(raw_data)
        return raw_data + signature

    async def decode_message(self, raw_msg: bytes) -> dict:
        try:
            raw_data = raw_msg[:-64]
            signature = raw_msg[-64:]
            
            message = json.loads(raw_data.decode())
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(message["pub_key"]))
            pub_key.verify(signature, raw_data)
            
            return message
        except (json.JSONDecodeError, InvalidSignature, KeyError) as e:
            logger.error(f"Invalid message: {str(e)}")
            raise

    async def process_message(self, message: dict, writer: asyncio.StreamWriter):
        msg_type = message.get("type")
        
        if msg_type == "handshake":
            await self.handle_handshake(message, writer)
        elif msg_type == "chunk_announce":
            await self.handle_chunk_announce(message)
        elif msg_type == "chunk_request":
            await self.handle_chunk_request(message, writer)
        elif msg_type == "peer_exchange":
            await self.handle_peer_exchange(message)
        elif msg_type == "heartbeat":
            pass  # Update peer status
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def handle_handshake(self, message: dict, writer: asyncio.StreamWriter):
        peer_id = message["node_id"]
        async with self.lock:
            self.peers[peer_id] = writer
        logger.info(f"Handshake completed with {peer_id}")
        
        # Change peer list
        await self.send_peer_list(writer)
        
        # Announce available chunks
        await self.announce_chunks(writer)

    async def handle_chunk_announce(self, message: dict):
        chunk_hash = message["chunk_hash"]
        peers = message["peers"]
        
        async with self.lock:
            self.routing_table[chunk_hash] = peers
            logger.info(f"Updated routing table for chunk {chunk_hash[:8]}")

    async def handle_chunk_request(self, message: dict, writer: asyncio.StreamWriter):
        chunk_hash = message["chunk_hash"]
        if chunk_hash in self.chunks:
            response = {
                "type": "chunk_response",
                "chunk_hash": chunk_hash,
                "data": self.chunks[chunk_hash].hex()
            }
            await self.send_message(response, writer)
        else:
            logger.warning(f"Requested chunk not found: {chunk_hash[:8]}")

    async def handle_peer_exchange(self, message: dict):
        new_peers = message["peers"]
        for peer in new_peers:
            if peer not in self.peers:
                host, port = peer.split(":")
                asyncio.create_task(self.connect_to_peer(host, int(port)))

    async def announce_chunks(self, writer: asyncio.StreamWriter):
        async with self.lock:
            chunk_hashes = list(self.chunks.keys())
        
        announcement = {
            "type": "chunk_announce",
            "chunks": chunk_hashes,
            "node_id": f"{self.host}:{self.port}"
        }
        await self.send_message(announcement, writer)

    async def send_peer_list(self, writer: asyncio.StreamWriter):
        async with self.lock:
            peer_list = list(self.peers.keys())
        
        message = {
            "type": "peer_exchange",
            "peers": peer_list
        }
        await self.send_message(message, writer)

    async def heartbeat(self, writer: asyncio.StreamWriter):
        while True:
            await asyncio.sleep(30)
            try:
                await self.send_message({"type": "heartbeat"}, writer)
            except ConnectionResetError:
                break

    async def remove_peer(self, writer: asyncio.StreamWriter):
        async with self.lock:
            for peer_id, w in list(self.peers.items()):
                if w is writer:
                    del self.peers[peer_id]
                    logger.info(f"Peer removed: {peer_id}")
                    
                    # Update routing table
                    for chunk_hash, peers in list(self.routing_table.items()):
                        if peer_id in peers:
                            self.routing_table[chunk_hash].remove(peer_id)