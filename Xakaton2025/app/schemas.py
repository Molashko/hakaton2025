from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal

# Executor schemas
class ExecutorBase(BaseModel):
    name: str
    parameters: Optional[Dict[str, Any]] = None
    active: bool = True
    daily_limit: int = 100

class ExecutorCreate(ExecutorBase):
    pass

class ExecutorUpdate(BaseModel):
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    daily_limit: Optional[int] = None

class Executor(ExecutorBase):
    id: int
    assigned_today: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Task schemas
class TaskBase(BaseModel):
    external_id: str
    parameters: Optional[Dict[str, Any]] = None
    weight: int = 1
    parent_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    weight: Optional[int] = None

class Task(TaskBase):
    id: int
    status: str = "pending"
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Assignment schemas
class AssignmentBase(BaseModel):
    task_id: int
    executor_id: int
    score: Optional[Decimal] = None

class AssignmentCreate(AssignmentBase):
    pass

class Assignment(AssignmentBase):
    id: int
    assigned_at: datetime
    
    class Config:
        from_attributes = True

# Rule schemas
class RuleSetBase(BaseModel):
    name: str
    rules: Dict[str, Any]
    active: bool = True

class RuleSetCreate(RuleSetBase):
    pass

class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

class RuleSet(RuleSetBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# KPI schemas
class KPIAggregate(BaseModel):
    day: date
    mae: Optional[Decimal] = None
    avg_latency: Optional[Decimal] = None
    total_assigned: int = 0
    
    class Config:
        from_attributes = True

# API Response schemas
class TaskAssignmentResponse(BaseModel):
    task_id: int
    executor_id: int
    score: Optional[Decimal] = None
    assigned_at: datetime

class ExecutorStats(BaseModel):
    executor_id: int
    name: str
    assigned_today: int
    daily_limit: int
    utilization: float

class DistributionStats(BaseModel):
    total_tasks: int
    total_executors: int
    assignments: List[ExecutorStats]
    mae: Optional[Decimal] = None
    avg_latency: Optional[Decimal] = None
