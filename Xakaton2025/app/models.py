from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Executor(Base):
    __tablename__ = "executors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    parameters = Column(JSON, nullable=True)
    active = Column(Boolean, default=True)
    daily_limit = Column(Integer, default=100)
    assigned_today = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    assignments = relationship("Assignment", back_populates="executor")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, nullable=False)
    status = Column(String(50), default="pending")
    parameters = Column(JSON, nullable=True)
    weight = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    assignments = relationship("Assignment", back_populates="task")
    parent = relationship("Task", remote_side=[id])

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("executors.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Numeric(10, 4), nullable=True)
    
    task = relationship("Task", back_populates="assignments")
    executor = relationship("Executor", back_populates="assignments")

class RuleSet(Base):
    __tablename__ = "rule_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rules = Column(JSON, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    
    key = Column(String(255), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Outbox(Base):
    __tablename__ = "outbox"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

class AggregatesKPI(Base):
    __tablename__ = "aggregates_kpi"
    
    id = Column(Integer, primary_key=True, index=True)
    day = Column(Date, nullable=False, unique=True)
    mae = Column(Numeric(10, 4), nullable=True)
    avg_latency = Column(Numeric(10, 4), nullable=True)
    total_assigned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
