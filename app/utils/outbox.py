import json
import asyncio
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models import Assignment, Executor, Task, AggregatesKPI
from datetime import datetime, date, timedelta
from decimal import Decimal

class OutboxProcessor:
    """Process outbox events for retry logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_outbox_events(self):
        """Process pending outbox events"""
        from app.models import Outbox
        
        result = await self.db.execute(
            select(Outbox).where(Outbox.processed == False).limit(100)
        )
        events = result.scalars().all()
        
        processed_count = 0
        for event in events:
            try:
                await self.process_event(event)
                event.processed = True
                event.processed_at = datetime.utcnow()
                processed_count += 1
            except Exception as e:
                print(f"Error processing outbox event {event.id}: {e}")
                # Keep event unprocessed for retry
        
        await self.db.commit()
        return processed_count
    
    async def process_event(self, event):
        """Process a single outbox event"""
        event_type = event.event_type
        payload = event.payload
        
        if event_type == "assignment_created":
            await self.handle_assignment_created(payload)
        elif event_type == "executor_updated":
            await self.handle_executor_updated(payload)
        else:
            print(f"Unknown event type: {event_type}")
    
    async def handle_assignment_created(self, payload: Dict[str, Any]):
        """Handle assignment created event"""
        # Could send notifications, update external systems, etc.
        print(f"Assignment created: {payload}")
    
    async def handle_executor_updated(self, payload: Dict[str, Any]):
        """Handle executor updated event"""
        # Could sync with external systems, etc.
        print(f"Executor updated: {payload}")

class KPIAggregator:
    """Aggregate KPI data for reporting"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_daily_kpi(self, target_date: date = None):
        """Calculate KPI for a specific day"""
        if target_date is None:
            target_date = date.today()
        
        # Get assignments for the day
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        result = await self.db.execute(
            select(Assignment)
            .where(Assignment.assigned_at >= start_datetime)
            .where(Assignment.assigned_at <= end_datetime)
        )
        assignments = result.scalars().all()
        
        if not assignments:
            return None
        
        # Calculate MAE (Mean Absolute Error) for fairness
        executor_loads = {}
        for assignment in assignments:
            executor_id = assignment.executor_id
            if executor_id not in executor_loads:
                executor_loads[executor_id] = 0
            executor_loads[executor_id] += 1
        
        if executor_loads:
            avg_load = sum(executor_loads.values()) / len(executor_loads)
            mae = sum(abs(load - avg_load) for load in executor_loads.values()) / len(executor_loads)
        else:
            mae = 0
        
        # Calculate average latency (simplified)
        avg_latency = 0.1  # Placeholder - would need actual timing data
        
        # Store or update KPI record
        result = await self.db.execute(
            select(AggregatesKPI).where(AggregatesKPI.day == target_date)
        )
        kpi_record = result.scalar_one_or_none()
        
        if kpi_record:
            kpi_record.mae = Decimal(str(mae))
            kpi_record.avg_latency = Decimal(str(avg_latency))
            kpi_record.total_assigned = len(assignments)
            kpi_record.updated_at = datetime.utcnow()
        else:
            kpi_record = AggregatesKPI(
                day=target_date,
                mae=Decimal(str(mae)),
                avg_latency=Decimal(str(avg_latency)),
                total_assigned=len(assignments)
            )
            self.db.add(kpi_record)
        
        await self.db.commit()
        return kpi_record
    
    async def get_kpi_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get KPI trend for the last N days"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        result = await self.db.execute(
            select(AggregatesKPI)
            .where(AggregatesKPI.day >= start_date)
            .where(AggregatesKPI.day <= end_date)
            .order_by(AggregatesKPI.day)
        )
        kpi_records = result.scalars().all()
        
        return [
            {
                "day": record.day.isoformat(),
                "mae": float(record.mae) if record.mae else 0,
                "avg_latency": float(record.avg_latency) if record.avg_latency else 0,
                "total_assigned": record.total_assigned
            }
            for record in kpi_records
        ]

async def main():
    """Main function for background tasks"""
    async with AsyncSessionLocal() as db:
        # Process outbox events
        processor = OutboxProcessor(db)
        processed = await processor.process_outbox_events()
        print(f"Processed {processed} outbox events")
        
        # Calculate daily KPI
        aggregator = KPIAggregator(db)
        kpi = await aggregator.calculate_daily_kpi()
        if kpi:
            print(f"Calculated KPI for {kpi.day}: MAE={kpi.mae}, Total={kpi.total_assigned}")

if __name__ == "__main__":
    asyncio.run(main())
