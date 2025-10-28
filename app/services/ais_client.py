import httpx
from typing import Dict, Any, List
from app.config import settings

class AISClient:
    """Client for external AIS (Automated Information System)"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_executors(self) -> List[Dict[str, Any]]:
        """Get all executors from external AIS"""
        try:
            response = await self.client.get(f"{self.base_url}/ais/executors")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error fetching executors from AIS: {e}")
            return []
    
    async def create_executor(self, executor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create executor in external AIS"""
        try:
            response = await self.client.post(
                f"{self.base_url}/ais/executors",
                json=executor_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error creating executor in AIS: {e}")
            raise
    
    async def update_executor(self, executor_id: int, executor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update executor in external AIS"""
        try:
            response = await self.client.put(
                f"{self.base_url}/ais/executors/{executor_id}",
                json=executor_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error updating executor in AIS: {e}")
            raise
    
    async def delete_executor(self, executor_id: int) -> bool:
        """Delete executor from external AIS"""
        try:
            response = await self.client.delete(f"{self.base_url}/ais/executors/{executor_id}")
            response.raise_for_status()
            return True
        except httpx.RequestError as e:
            print(f"Error deleting executor from AIS: {e}")
            return False
    
    async def get_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tasks from external AIS"""
        try:
            response = await self.client.get(
                f"{self.base_url}/ais/tasks",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error fetching tasks from AIS: {e}")
            return []
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create task in external AIS"""
        try:
            response = await self.client.post(
                f"{self.base_url}/ais/tasks",
                json=task_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error creating task in AIS: {e}")
            raise
    
    async def get_assignments(self, executor_id: int = None) -> List[Dict[str, Any]]:
        """Get assignments from external AIS"""
        try:
            params = {}
            if executor_id:
                params["executor_id"] = executor_id
            
            response = await self.client.get(
                f"{self.base_url}/ais/assignments",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error fetching assignments from AIS: {e}")
            return []
    
    async def sync_executors(self) -> int:
        """Sync executors from external AIS to local database"""
        from app.database import AsyncSessionLocal
        from app.models import Executor
        from sqlalchemy import select
        
        ais_executors = await self.get_executors()
        synced_count = 0
        
        async with AsyncSessionLocal() as db:
            for ais_executor in ais_executors:
                # Check if executor exists
                result = await db.execute(
                    select(Executor).where(Executor.id == ais_executor["id"])
                )
                existing_executor = result.scalar_one_or_none()
                
                if existing_executor:
                    # Update existing
                    existing_executor.name = ais_executor["name"]
                    existing_executor.parameters = ais_executor.get("parameters")
                    existing_executor.active = ais_executor.get("active", True)
                    existing_executor.daily_limit = ais_executor.get("daily_limit", 100)
                else:
                    # Create new
                    new_executor = Executor(
                        id=ais_executor["id"],
                        name=ais_executor["name"],
                        parameters=ais_executor.get("parameters"),
                        active=ais_executor.get("active", True),
                        daily_limit=ais_executor.get("daily_limit", 100)
                    )
                    db.add(new_executor)
                
                synced_count += 1
            
            await db.commit()
        
        return synced_count
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
