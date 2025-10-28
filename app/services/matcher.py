import json
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from app.models import Executor, Task, Assignment, RuleSet
from app.schemas import ExecutorStats, DistributionStats
from app.rule_engine import RuleEngine
from app.utils.redis_client import redis_client
import time

class MatcherService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_engine = RuleEngine()
    
    async def find_best_executor(self, task: Task) -> Optional[Tuple[Executor, float]]:
        """Find the best executor for a task based on rules and weights"""
        
        # Get active executors
        result = await self.db.execute(
            select(Executor).where(Executor.active == True)
        )
        executors = result.scalars().all()
        
        if not executors:
            return None
        
        # Get active rule set
        rule_set_result = await self.db.execute(
            select(RuleSet).where(RuleSet.active == True).order_by(desc(RuleSet.created_at))
        )
        rule_set = rule_set_result.scalar_one_or_none()
        
        best_executor = None
        best_score = -1.0
        
        for executor in executors:
            # Check if executor has capacity
            if executor.assigned_today >= executor.daily_limit:
                continue
            
            # Create context for rule evaluation
            context = {
                "task": {
                    "id": task.id,
                    "external_id": task.external_id,
                    "parameters": task.parameters or {},
                    "weight": task.weight
                },
                "executor": {
                    "id": executor.id,
                    "name": executor.name,
                    "parameters": executor.parameters or {},
                    "assigned_today": executor.assigned_today,
                    "daily_limit": executor.daily_limit
                }
            }
            
            # Apply rules if available
            if rule_set and rule_set.rules:
                rules = rule_set.rules.get('conditions', [])
                if not self.rule_engine.evaluate_rule_set(rules, context):
                    continue
            
            # Calculate weight/score
            weight_rules = rule_set.rules.get('weights', []) if rule_set else []
            base_weight = 1.0
            if weight_rules:
                base_weight = self.rule_engine.calculate_weight(weight_rules, context)
            
            # Calculate fairness score (inverse of current load)
            utilization = executor.assigned_today / executor.daily_limit if executor.daily_limit > 0 else 0
            fairness_score = 1.0 - utilization
            
            # Final score combines weight and fairness
            final_score = base_weight * fairness_score
            
            if final_score > best_score:
                best_score = final_score
                best_executor = executor
        
        if best_executor:
            return best_executor, best_score
        
        return None
    
    async def assign_task(self, task: Task) -> Optional[Assignment]:
        """Assign a task to the best available executor"""
        start_time = time.time()
        
        result = await self.find_best_executor(task)
        if not result:
            return None
        
        executor, score = result
        
        # Create assignment
        assignment = Assignment(
            task_id=task.id,
            executor_id=executor.id,
            score=Decimal(str(score))
        )
        
        # Update executor's daily count
        executor.assigned_today += 1
        
        # Update task status
        task.status = "assigned"
        
        self.db.add(assignment)
        await self.db.commit()
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Send to Redis for metrics
        await redis_client.add_to_stream("assignment_metrics", {
            "task_id": str(task.id),
            "executor_id": str(executor.id),
            "score": str(score),
            "latency": str(latency),
            "timestamp": str(int(time.time()))
        })
        
        return assignment
    
    async def get_distribution_stats(self) -> DistributionStats:
        """Get current distribution statistics"""
        
        # Get executor stats
        result = await self.db.execute(
            select(Executor).where(Executor.active == True)
        )
        executors = result.scalars().all()
        
        executor_stats = []
        total_assigned = 0
        
        for executor in executors:
            utilization = executor.assigned_today / executor.daily_limit if executor.daily_limit > 0 else 0
            executor_stats.append(ExecutorStats(
                executor_id=executor.id,
                name=executor.name,
                assigned_today=executor.assigned_today,
                daily_limit=executor.daily_limit,
                utilization=utilization
            ))
            total_assigned += executor.assigned_today
        
        # Calculate MAE (Mean Absolute Error) for fairness
        if executor_stats:
            avg_load = sum(stat.utilization for stat in executor_stats) / len(executor_stats)
            mae = sum(abs(stat.utilization - avg_load) for stat in executor_stats) / len(executor_stats)
        else:
            mae = None
        
        # Get total tasks
        task_count_result = await self.db.execute(
            select(func.count(Task.id))
        )
        total_tasks = task_count_result.scalar()
        
        return DistributionStats(
            total_tasks=total_tasks,
            total_executors=len(executor_stats),
            assignments=executor_stats,
            mae=Decimal(str(mae)) if mae is not None else None,
            avg_latency=None  # Will be calculated from metrics
        )
    
    async def reset_daily_counts(self):
        """Reset daily assignment counts for all executors"""
        await self.db.execute(
            select(Executor).update().values(assigned_today=0)
        )
        await self.db.commit()
    
    async def get_executor_performance(self, executor_id: int, days: int = 7) -> Dict[str, Any]:
        """Get performance metrics for a specific executor"""
        
        # Get assignments for the last N days
        result = await self.db.execute(
            select(Assignment, Task)
            .join(Task)
            .where(Assignment.executor_id == executor_id)
            .order_by(desc(Assignment.assigned_at))
            .limit(days * 20)  # Assuming max 20 tasks per day
        )
        
        assignments = result.all()
        
        # Calculate metrics
        total_assignments = len(assignments)
        avg_score = sum(float(a.Assignment.score or 0) for a in assignments) / total_assignments if total_assignments > 0 else 0
        
        return {
            "executor_id": executor_id,
            "total_assignments": total_assignments,
            "avg_score": avg_score,
            "assignments": [
                {
                    "task_id": a.Assignment.task_id,
                    "assigned_at": a.Assignment.assigned_at.isoformat(),
                    "score": float(a.Assignment.score or 0)
                }
                for a in assignments
            ]
        }
