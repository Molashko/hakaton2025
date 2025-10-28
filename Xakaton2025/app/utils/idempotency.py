import hashlib
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import IdempotencyKey
from datetime import datetime, timedelta

class IdempotencyManager:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_and_set_key(self, key: str, ttl_hours: int = 24) -> bool:
        """
        Check if idempotency key exists and set it if not.
        Returns True if key is new (should process), False if exists (should skip).
        """
        # Check if key exists
        result = await self.db.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key)
        )
        existing_key = result.scalar_one_or_none()
        
        if existing_key:
            return False
        
        # Set new key
        new_key = IdempotencyKey(key=key)
        self.db.add(new_key)
        await self.db.commit()
        return True
    
    async def cleanup_expired_keys(self, ttl_hours: int = 24):
        """Clean up expired idempotency keys"""
        cutoff_time = datetime.utcnow() - timedelta(hours=ttl_hours)
        await self.db.execute(
            select(IdempotencyKey).where(IdempotencyKey.created_at < cutoff_time)
        )
        await self.db.commit()

def generate_idempotency_key(data: dict) -> str:
    """Generate idempotency key from request data"""
    # Sort keys to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(sorted_data.encode()).hexdigest()
