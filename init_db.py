#!/usr/bin/env python3
"""
Database initialization script for Executor Balancer
Creates initial data and runs migrations
"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal, async_engine
from app.models import Base, Executor, RuleSet
from app.rule_engine import EXAMPLE_RULES

async def create_tables():
    """Create all database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created")

async def create_initial_data():
    """Create initial data"""
    async with AsyncSessionLocal() as db:
        # Check if data already exists
        result = await db.execute(select(Executor))
        existing_executors = result.scalars().all()
        
        if existing_executors:
            print("Initial data already exists, skipping...")
            return
        
        # Create sample executors
        executors = [
            Executor(
                name="Alice Johnson",
                parameters={
                    "skills": ["python", "fastapi", "sql"],
                    "experience": "senior",
                    "department": "backend"
                },
                active=True,
                daily_limit=80,
                assigned_today=0
            ),
            Executor(
                name="Bob Smith",
                parameters={
                    "skills": ["python", "django", "postgresql"],
                    "experience": "middle",
                    "department": "backend"
                },
                active=True,
                daily_limit=60,
                assigned_today=0
            ),
            Executor(
                name="Carol Davis",
                parameters={
                    "skills": ["javascript", "react", "nodejs"],
                    "experience": "senior",
                    "department": "frontend"
                },
                active=True,
                daily_limit=70,
                assigned_today=0
            ),
            Executor(
                name="David Wilson",
                parameters={
                    "skills": ["python", "machine_learning", "pandas"],
                    "experience": "senior",
                    "department": "data"
                },
                active=True,
                daily_limit=50,
                assigned_today=0
            ),
            Executor(
                name="Eva Brown",
                parameters={
                    "skills": ["devops", "docker", "kubernetes"],
                    "experience": "middle",
                    "department": "infrastructure"
                },
                active=True,
                daily_limit=40,
                assigned_today=0
            )
        ]
        
        for executor in executors:
            db.add(executor)
        
        # Create default rule set
        default_rules = RuleSet(
            name="Default Distribution Rules",
            rules={
                "conditions": [
                    {
                        "operator": "eq",
                        "field": "executor.active",
                        "value": True
                    },
                    {
                        "operator": "lt",
                        "field": "executor.assigned_today",
                        "value": "executor.daily_limit"
                    }
                ],
                "weights": [
                    {
                        "condition": {
                            "operator": "eq",
                            "field": "task.parameters.priority",
                            "value": "high"
                        },
                        "weight": 2.0
                    },
                    {
                        "condition": {
                            "operator": "lt",
                            "field": "executor.assigned_today",
                            "value": 20
                        },
                        "weight": 1.5
                    },
                    {
                        "condition": {
                            "operator": "in",
                            "field": "executor.parameters.skills",
                            "value": ["python", "fastapi"]
                        },
                        "weight": 1.2
                    }
                ]
            },
            active=True
        )
        
        db.add(default_rules)
        
        await db.commit()
        print(f"Created {len(executors)} sample executors")
        print("Created default rule set")

async def main():
    """Main initialization function"""
    print("Initializing Executor Balancer database...")
    
    try:
        # Create tables
        await create_tables()
        
        # Create initial data
        await create_initial_data()
        
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Error during initialization: {e}")
        sys.exit(1)
    
    finally:
        await async_engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
