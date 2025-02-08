import os
import json
import asyncio
import aiofiles
import logging
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Dict, Optional
import node

# logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TorrentChainP2P")

class ChunkManager:
    def __init__(self, node_id: str, storage_path: str = "node_storage", chunk_ttl: int = 604800):
        self.node_id = node_id
        self.storage_path = os.path.join(storage_path, node_id)
        self.chunk_ttl = chunk_ttl  # 7 days in seconds
        self.metadata_file = os.path.join(self.storage_path, "metadata.json")
        self.lock = asyncio.Lock()
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize in-memory index
        self.chunk_index: Dict[str, dict] = {}
        asyncio.create_task(self.load_persisted_chunks())

    async def chunk_path(self, chunk_hash: str) -> str:
        return os.path.join(self.storage_path, f"{chunk_hash}.chunk")

    async def load_persisted_chunks(self):
        """Load chunks and metadata from disk during initialization"""
        try:
            async with self.lock:
                # Load metadata
                if os.path.exists(self.metadata_file):
                    async with aiofiles.open(self.metadata_file, "r") as f:
                        metadata = json.loads(await f.read())
                        self.chunk_index = metadata.get("chunks", {})
                
                # Validate persisted chunks against metadata
                for chunk_hash in list(self.chunk_index.keys()):
                    chunk_file = await self.chunk_path(chunk_hash)
                    if not os.path.exists(chunk_file):
                        del self.chunk_index[chunk_hash]
                    elif not await self.validate_chunk(chunk_hash):
                        await self.delete_chunk(chunk_hash)

        except Exception as e:
            logger.error(f"Failed to load persisted chunks: {str(e)}")

    async def save_metadata(self):
        """Persist metadata to disk asynchronously"""
        async with self.lock:
            async with aiofiles.open(self.metadata_file, "w") as f:
                metadata = {
                    "node_id": self.node_id,
                    "chunks": self.chunk_index,
                    "timestamp": datetime.now().isoformat()
                }
                await f.write(json.dumps(metadata, indent=2))

    async def store_chunk(self, chunk_hash: str, data: bytes, peers: list) -> bool:
        """Store chunk with validation and replication tracking"""
        try:
            if not await self.validate_chunk_data(chunk_hash, data):
                logger.error(f"Invalid chunk data for {chunk_hash[:8]}")
                return False

            async with self.lock:
                chunk_file = await self.chunk_path(chunk_hash)
                async with aiofiles.open(chunk_file, "wb") as f:
                    await f.write(data)

                # Update metadata
                self.chunk_index[chunk_hash] = {
                    "size": len(data),
                    "peers": peers,
                    "created_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(seconds=self.chunk_ttl)).isoformat()
                }
                
                await self.save_metadata()
                return True

        except (IOError, OSError) as e:
            logger.error(f"Storage error for {chunk_hash[:8]}: {str(e)}")
            return False

    async def retrieve_chunk(self, chunk_hash: str) -> Optional[bytes]:
        """Retrieve chunk data from disk with validation"""
        try:
            async with self.lock:
                if chunk_hash not in self.chunk_index:
                    return None

                chunk_file = await self.chunk_path(chunk_hash)
                async with aiofiles.open(chunk_file, "rb") as f:
                    data = await f.read()

                if await self.validate_chunk_data(chunk_hash, data):
                    return data
                return None

        except (FileNotFoundError, IOError) as e:
            logger.warning(f"Chunk retrieval failed for {chunk_hash[:8]}: {str(e)}")
            return None

    async def delete_chunk(self, chunk_hash: str):
        """Remove chunk and update metadata"""
        async with self.lock:
            try:
                if chunk_hash in self.chunk_index:
                    os.remove(await self.chunk_path(chunk_hash))
                    del self.chunk_index[chunk_hash]
                    await self.save_metadata()
            except Exception as e:
                logger.error(f"Failed to delete chunk {chunk_hash[:8]}: {str(e)}")

    async def validate_chunk(self, chunk_hash: str) -> bool:
        """Validate chunk existence and metadata"""
        async with self.lock:
            if chunk_hash not in self.chunk_index:
                return False

            chunk_file = await self.chunk_path(chunk_hash)
            if not os.path.exists(chunk_file):
                return False

            expires_at = datetime.fromisoformat(self.chunk_index[chunk_hash]["expires_at"])
            return datetime.utcnow() < expires_at

    async def validate_chunk_data(self, chunk_hash: str, data: bytes) -> bool:
        """Cryptographic validation of chunk data"""
        computed_hash = sha256(data).hexdigest()
        return computed_hash == chunk_hash

    async def cleanup_expired_chunks(self):
        """Background task to remove expired chunks"""
        while True:
            await asyncio.sleep(3600)  # Run hourly
            async with self.lock:
                now = datetime.utcnow()
                for chunk_hash in list(self.chunk_index.keys()):
                    expires_at = datetime.fromisoformat(self.chunk_index[chunk_hash]["expires_at"])
                    if now >= expires_at:
                        await self.delete_chunk(chunk_hash)
                logger.info("Completed expired chunk cleanup")

class Node:
    def __init__(self, host: str, port: int, priv_key=None):
        # ... (previous initialization code)
        
        # Add persistent storage
        self.storage = ChunkManager(
            node_id=f"{host}:{port}",
            storage_path="p2p_storage",
            chunk_ttl=604800  # 7 days
        )
        
        # Start background tasks
        asyncio.create_task(self.storage.cleanup_expired_chunks())

    async def store_chunk(self, data: bytes, peers: list) -> str:
        """Store data as chunk with replication tracking"""
        chunk_hash = sha256(data).hexdigest()
        if await self.storage.store_chunk(chunk_hash, data, peers):
            await self.announce_chunks()  # Update network about new chunk
            return chunk_hash
        raise ValueError("Failed to store chunk")

    async def retrieve_chunk(self, chunk_hash: str) -> Optional[bytes]:
        """Retrieve chunk from local storage or network"""
        # Try local storage first
        data = await self.storage.retrieve_chunk(chunk_hash)
        if data:
            return data
        
        # If not found, query network
        await self.request_chunk_from_peers(chunk_hash)
        return None

    async def request_chunk_from_peers(self, chunk_hash: str):
        """Query peers for missing chunk"""
        message = {
            "type": "chunk_request",
            "chunk_hash": chunk_hash,
            "requestor": f"{self.host}:{self.port}"
        }
        await self.broadcast_message(message)

    async def handle_chunk_response(self, message: dict, writer: asyncio.StreamWriter):
        """Process incoming chunk data"""
        chunk_hash = message["chunk_hash"]
        data = bytes.fromhex(message["data"])
        
        if await self.storage.validate_chunk_data(chunk_hash, data):
            await self.storage.store_chunk(chunk_hash, data, [])
            logger.info(f"Stored new chunk: {chunk_hash[:8]}")
        else:
            logger.warning(f"Received invalid chunk: {chunk_hash[:8]}")