import redis.asyncio as redis
import json
from typing import Dict, Any, Optional
from app.config import settings

class RedisClient:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
    
    async def add_to_stream(self, stream_name: str, data: Dict[str, Any]) -> str:
        """Add message to Redis Stream"""
        return await self.redis.xadd(stream_name, data)
    
    async def read_from_stream(self, stream_name: str, consumer_group: str, 
                              consumer_name: str, count: int = 1) -> list:
        """Read messages from Redis Stream using consumer group"""
        try:
            # Try to read from consumer group
            messages = await self.redis.xreadgroup(
                consumer_group, consumer_name, 
                {stream_name: ">"}, count=count, block=1000
            )
            return messages
        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                # Create consumer group if it doesn't exist
                await self.redis.xgroup_create(stream_name, consumer_group, id="0", mkstream=True)
                return await self.redis.xreadgroup(
                    consumer_group, consumer_name, 
                    {stream_name: ">"}, count=count, block=1000
                )
            raise
    
    async def ack_message(self, stream_name: str, consumer_group: str, message_id: str):
        """Acknowledge message processing"""
        await self.redis.xack(stream_name, consumer_group, message_id)
    
    async def get_stream_length(self, stream_name: str) -> int:
        """Get length of stream"""
        return await self.redis.xlen(stream_name)
    
    async def set_cache(self, key: str, value: Any, expire: int = 3600):
        """Set cache value"""
        await self.redis.setex(key, expire, json.dumps(value))
    
    async def get_cache(self, key: str) -> Optional[Any]:
        """Get cache value"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def acquire_lock(self, lock_name: str, timeout: int = 10) -> bool:
        """Acquire distributed lock"""
        return await self.redis.set(lock_name, "locked", nx=True, ex=timeout)
    
    async def release_lock(self, lock_name: str):
        """Release distributed lock"""
        await self.redis.delete(lock_name)
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()

# Global Redis client instance
redis_client = RedisClient()
