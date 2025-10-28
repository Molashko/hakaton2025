from fastapi import FastAPI, Depends, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional, Dict, Any
import json
import time
from datetime import datetime, date
import pandas as pd
import io

from app.database import get_db
from app.models import Executor, Task, Assignment, RuleSet, AggregatesKPI
from app.schemas import (
    ExecutorCreate, ExecutorUpdate, Executor as ExecutorSchema,
    TaskCreate, TaskUpdate, Task as TaskSchema,
    Assignment as AssignmentSchema,
    RuleSetCreate, RuleSetUpdate, RuleSet as RuleSetSchema,
    TaskAssignmentResponse, DistributionStats, KPIAggregate
)
from app.services.matcher import MatcherService
from app.services.ais_client import AISClient
from app.services.metrics import metrics_collector
from app.utils.idempotency import IdempotencyManager, generate_idempotency_key
from app.utils.redis_client import redis_client
from app.worker import task_worker
from app.config import settings

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Executor Balancer - система справедливого распределения заявок"
)

# Start metrics server
metrics_collector.start_server()

# API Routes

@app.post("/v1/tasks", response_model=TaskAssignmentResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую заявку и добавить в очередь распределения"""
    
    # Check idempotency
    idempotency_manager = IdempotencyManager(db)
    if idempotency_key:
        if not await idempotency_manager.check_and_set_key(idempotency_key):
            raise HTTPException(status_code=409, detail="Duplicate request")
    else:
        # Generate idempotency key from request data
        key_data = task_data.dict()
        idempotency_key = generate_idempotency_key(key_data)
        if not await idempotency_manager.check_and_set_key(idempotency_key):
            raise HTTPException(status_code=409, detail="Duplicate request")
    
    # Create task
    task = Task(
        external_id=task_data.external_id,
        parameters=task_data.parameters,
        weight=task_data.weight,
        parent_id=task_data.parent_id
    )
    
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Add to processing queue
    await task_worker.add_task_to_queue(task.id, task.weight)
    
    return TaskAssignmentResponse(
        task_id=task.id,
        executor_id=0,  # Will be assigned by worker
        assigned_at=datetime.utcnow()
    )

@app.get("/v1/executors", response_model=List[ExecutorSchema])
async def get_executors(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Получить список исполнителей"""
    query = select(Executor)
    if active_only:
        query = query.where(Executor.active == True)
    
    result = await db.execute(query)
    executors = result.scalars().all()
    return executors

@app.post("/v1/executors", response_model=ExecutorSchema)
async def create_executor(
    executor_data: ExecutorCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать нового исполнителя"""
    executor = Executor(**executor_data.dict())
    db.add(executor)
    await db.commit()
    await db.refresh(executor)
    return executor

@app.put("/v1/executors/{executor_id}", response_model=ExecutorSchema)
async def update_executor(
    executor_id: int,
    executor_data: ExecutorUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить исполнителя"""
    result = await db.execute(select(Executor).where(Executor.id == executor_id))
    executor = result.scalar_one_or_none()
    
    if not executor:
        raise HTTPException(status_code=404, detail="Executor not found")
    
    update_data = executor_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(executor, field, value)
    
    await db.commit()
    await db.refresh(executor)
    return executor

@app.post("/v1/executors/cache-sync")
async def sync_executors_cache(db: AsyncSession = Depends(get_db)):
    """Синхронизировать исполнителей с внешним АИС"""
    ais_client = AISClient()
    try:
        synced_count = await ais_client.sync_executors()
        
        # Update metrics
        result = await db.execute(select(func.count(Executor.id)).where(Executor.active == True))
        active_count = result.scalar()
        metrics_collector.update_active_executors(active_count)
        
        return {"synced_executors": synced_count, "active_executors": active_count}
    finally:
        await ais_client.close()

@app.get("/v1/distribution/stats", response_model=DistributionStats)
async def get_distribution_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику распределения"""
    matcher = MatcherService(db)
    stats = await matcher.get_distribution_stats()
    
    # Update fairness metric
    if stats.mae:
        metrics_collector.update_fairness_mae(float(stats.mae))
    
    # Update executor utilization metrics
    for assignment in stats.assignments:
        metrics_collector.update_executor_utilization(
            assignment.executor_id,
            assignment.name,
            assignment.utilization
        )
    
    return stats

@app.get("/v1/exports/kpi", response_class=FileResponse)
async def export_kpi(
    format: str = "excel",
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Экспорт KPI в Excel или JSON"""
    
    # Get KPI data
    result = await db.execute(
        select(AggregatesKPI)
        .order_by(desc(AggregatesKPI.day))
        .limit(days)
    )
    kpi_data = result.scalars().all()
    
    if format == "excel":
        # Create Excel file
        df = pd.DataFrame([
            {
                "day": kpi.day,
                "mae": float(kpi.mae) if kpi.mae else 0,
                "avg_latency": float(kpi.avg_latency) if kpi.avg_latency else 0,
                "total_assigned": kpi.total_assigned
            }
            for kpi in kpi_data
        ])
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='KPI', index=False)
        
        output.seek(0)
        
        return FileResponse(
            path=None,
            filename=f"kpi_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=output.getvalue()
        )
    
    else:  # JSON format
        return JSONResponse(content=[
            {
                "day": kpi.day.isoformat(),
                "mae": float(kpi.mae) if kpi.mae else 0,
                "avg_latency": float(kpi.avg_latency) if kpi.avg_latency else 0,
                "total_assigned": kpi.total_assigned
            }
            for kpi in kpi_data
        ])

@app.post("/v1/rules", response_model=RuleSetSchema)
async def create_rule_set(
    rule_data: RuleSetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать набор правил"""
    rule_set = RuleSet(**rule_data.dict())
    db.add(rule_set)
    await db.commit()
    await db.refresh(rule_set)
    return rule_set

@app.get("/v1/rules", response_model=List[RuleSetSchema])
async def get_rule_sets(db: AsyncSession = Depends(get_db)):
    """Получить наборы правил"""
    result = await db.execute(select(RuleSet))
    rule_sets = result.scalars().all()
    return rule_sets

@app.post("/v1/admin/reset-daily-counts")
async def reset_daily_counts(db: AsyncSession = Depends(get_db)):
    """Сбросить дневные счетчики исполнителей"""
    matcher = MatcherService(db)
    await matcher.reset_daily_counts()
    return {"message": "Daily counts reset successfully"}

@app.get("/v1/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.api_version
    }

# AIS Emulator endpoints

@app.get("/ais/executors")
async def ais_get_executors(db: AsyncSession = Depends(get_db)):
    """Эмулятор АИС: получить исполнителей"""
    result = await db.execute(select(Executor))
    executors = result.scalars().all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "parameters": e.parameters,
            "active": e.active,
            "daily_limit": e.daily_limit
        }
        for e in executors
    ]

@app.post("/ais/executors")
async def ais_create_executor(
    executor_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Эмулятор АИС: создать исполнителя"""
    executor = Executor(
        name=executor_data["name"],
        parameters=executor_data.get("parameters"),
        active=executor_data.get("active", True),
        daily_limit=executor_data.get("daily_limit", 100)
    )
    db.add(executor)
    await db.commit()
    await db.refresh(executor)
    return {
        "id": executor.id,
        "name": executor.name,
        "parameters": executor.parameters,
        "active": executor.active,
        "daily_limit": executor.daily_limit
    }

@app.get("/ais/tasks")
async def ais_get_tasks(
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Эмулятор АИС: получить заявки"""
    result = await db.execute(
        select(Task).order_by(desc(Task.created_at)).limit(limit)
    )
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "external_id": t.external_id,
            "status": t.status,
            "parameters": t.parameters,
            "weight": t.weight,
            "created_at": t.created_at.isoformat()
        }
        for t in tasks
    ]

@app.get("/ais/assignments")
async def ais_get_assignments(
    executor_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Эмулятор АИС: получить назначения"""
    query = select(Assignment, Task, Executor).join(Task).join(Executor)
    if executor_id:
        query = query.where(Assignment.executor_id == executor_id)
    
    result = await db.execute(query)
    assignments = result.all()
    
    return [
        {
            "id": a.Assignment.id,
            "task_id": a.Assignment.task_id,
            "executor_id": a.Assignment.executor_id,
            "executor_name": a.Executor.name,
            "assigned_at": a.Assignment.assigned_at.isoformat(),
            "score": float(a.Assignment.score) if a.Assignment.score else None
        }
        for a in assignments
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
