import asyncio
import json
import time
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Task, Assignment
from app.services.matcher import MatcherService
from app.services.metrics import metrics_collector
from app.utils.redis_client import redis_client
from loguru import logger

class TaskWorker:
    def __init__(self):
        self.running = False
        self.consumer_group = "task_processors"
        self.consumer_name = f"worker_{int(time.time())}"
        self.stream_name = "task_queue"
    
    async def start(self):
        """Start the worker"""
        self.running = True
        logger.info(f"Starting task worker {self.consumer_name}")
        
        # Start metrics server
        metrics_collector.start_server()
        
        while self.running:
            try:
                await self.process_tasks()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(f"Error in task worker: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Stopping task worker")
    
    async def process_tasks(self):
        """Process tasks from Redis Stream"""
        try:
            # Read messages from stream
            messages = await redis_client.read_from_stream(
                self.stream_name,
                self.consumer_group,
                self.consumer_name,
                count=10
            )
            
            if not messages:
                return
            
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    try:
                        await self.process_single_task(msg_id, fields)
                    except Exception as e:
                        logger.error(f"Error processing task {msg_id}: {e}")
                        # Still acknowledge to prevent reprocessing
                        await redis_client.ack_message(
                            self.stream_name,
                            self.consumer_group,
                            msg_id
                        )
        
        except Exception as e:
            logger.error(f"Error reading from stream: {e}")
    
    async def process_single_task(self, msg_id: str, fields: Dict[str, str]):
        """Process a single task message"""
        try:
            # Parse task data
            task_data = json.loads(fields.get('data', '{}'))
            task_id = task_data.get('task_id')
            
            if not task_id:
                logger.warning(f"No task_id in message {msg_id}")
                await redis_client.ack_message(
                    self.stream_name,
                    self.consumer_group,
                    msg_id
                )
                return
            
            # Get task from database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()
                
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    await redis_client.ack_message(
                        self.stream_name,
                        self.consumer_group,
                        msg_id
                    )
                    return
                
                if task.status != "pending":
                    logger.info(f"Task {task_id} already processed (status: {task.status})")
                    await redis_client.ack_message(
                        self.stream_name,
                        self.consumer_group,
                        msg_id
                    )
                    return
                
                # Process assignment
                matcher = MatcherService(db)
                assignment = await matcher.assign_task(task)
                
                if assignment:
                    logger.info(f"Assigned task {task_id} to executor {assignment.executor_id}")
                    
                    # Record metrics
                    metrics_collector.record_assignment(
                        assignment.executor_id,
                        "assigned",
                        float(fields.get('latency', 0))
                    )
                else:
                    logger.warning(f"No executor available for task {task_id}")
                    
                    # Record failed assignment
                    metrics_collector.record_assignment(
                        0,  # No executor
                        "failed",
                        float(fields.get('latency', 0))
                    )
                
                # Update queue lag metric
                queue_length = await redis_client.get_stream_length(self.stream_name)
                metrics_collector.update_queue_lag(queue_length)
            
            # Acknowledge message
            await redis_client.ack_message(
                self.stream_name,
                self.consumer_group,
                msg_id
            )
            
        except Exception as e:
            logger.error(f"Error processing task {msg_id}: {e}")
            # Still acknowledge to prevent infinite reprocessing
            await redis_client.ack_message(
                self.stream_name,
                self.consumer_group,
                msg_id
            )
    
    async def add_task_to_queue(self, task_id: int, priority: int = 1):
        """Add task to processing queue"""
        task_data = {
            "task_id": task_id,
            "priority": priority,
            "timestamp": int(time.time())
        }
        
        await redis_client.add_to_stream(
            self.stream_name,
            {"data": json.dumps(task_data)}
        )
        
        logger.info(f"Added task {task_id} to queue")

# Global worker instance
task_worker = TaskWorker()

async def main():
    """Main worker entry point"""
    worker = TaskWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await worker.stop()
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())
