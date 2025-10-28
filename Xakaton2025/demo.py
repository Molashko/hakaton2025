#!/usr/bin/env python3
"""
Demo script for Executor Balancer
Demonstrates the system capabilities with sample data
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import random

API_BASE_URL = "http://localhost:8000"

class ExecutorBalancerDemo:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_executor(self, name: str, skills: list, daily_limit: int = 100):
        """Create a new executor"""
        executor_data = {
            "name": name,
            "parameters": {
                "skills": skills,
                "experience": random.choice(["junior", "middle", "senior"]),
                "department": random.choice(["backend", "frontend", "data", "devops"])
            },
            "active": True,
            "daily_limit": daily_limit
        }
        
        async with self.session.post(f"{API_BASE_URL}/v1/executors", json=executor_data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Created executor: {name} (ID: {result['id']})")
                return result
            else:
                print(f"❌ Failed to create executor {name}: {response.status}")
                return None
    
    async def create_task(self, external_id: str, priority: str = "normal", category: str = "demo"):
        """Create a new task"""
        task_data = {
            "external_id": external_id,
            "parameters": {
                "priority": priority,
                "category": category,
                "source": "demo_script",
                "created_at": datetime.now().isoformat()
            },
            "weight": random.randint(1, 3)
        }
        
        async with self.session.post(f"{API_BASE_URL}/v1/tasks", json=task_data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"📝 Created task: {external_id} (ID: {result['task_id']})")
                return result
            else:
                print(f"❌ Failed to create task {external_id}: {response.status}")
                return None
    
    async def get_distribution_stats(self):
        """Get current distribution statistics"""
        async with self.session.get(f"{API_BASE_URL}/v1/distribution/stats") as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"❌ Failed to get distribution stats: {response.status}")
                return None
    
    async def get_executors(self):
        """Get list of executors"""
        async with self.session.get(f"{API_BASE_URL}/v1/executors") as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"❌ Failed to get executors: {response.status}")
                return None
    
    async def get_recent_assignments(self):
        """Get recent assignments"""
        async with self.session.get(f"{API_BASE_URL}/ais/assignments") as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"❌ Failed to get assignments: {response.status}")
                return None
    
    async def wait_for_assignments(self, expected_count: int, timeout: int = 30):
        """Wait for tasks to be assigned"""
        print(f"⏳ Waiting for {expected_count} assignments (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            assignments = await self.get_recent_assignments()
            if assignments and len(assignments) >= expected_count:
                print(f"✅ Found {len(assignments)} assignments")
                return assignments
            
            await asyncio.sleep(1)
        
        print(f"⏰ Timeout reached, found {len(assignments) if assignments else 0} assignments")
        return assignments or []

async def main():
    """Main demo function"""
    print("🎯 Executor Balancer Demo")
    print("=" * 50)
    
    async with ExecutorBalancerDemo() as demo:
        # Step 1: Create sample executors
        print("\n👥 Step 1: Creating sample executors...")
        
        executors_data = [
            ("Alice Johnson", ["python", "fastapi", "sql"], 80),
            ("Bob Smith", ["python", "django", "postgresql"], 60),
            ("Carol Davis", ["javascript", "react", "nodejs"], 70),
            ("David Wilson", ["python", "machine_learning", "pandas"], 50),
            ("Eva Brown", ["devops", "docker", "kubernetes"], 40)
        ]
        
        created_executors = []
        for name, skills, limit in executors_data:
            executor = await demo.create_executor(name, skills, limit)
            if executor:
                created_executors.append(executor)
        
        print(f"✅ Created {len(created_executors)} executors")
        
        # Step 2: Create sample tasks
        print("\n📝 Step 2: Creating sample tasks...")
        
        task_count = 20
        created_tasks = []
        
        priorities = ["low", "normal", "high"]
        categories = ["bug_fix", "feature", "refactor", "test", "documentation"]
        
        for i in range(task_count):
            external_id = f"DEMO_TASK_{i+1:03d}"
            priority = random.choice(priorities)
            category = random.choice(categories)
            
            task = await demo.create_task(external_id, priority, category)
            if task:
                created_tasks.append(task)
            
            # Small delay to simulate real-world task creation
            await asyncio.sleep(0.1)
        
        print(f"✅ Created {len(created_tasks)} tasks")
        
        # Step 3: Wait for assignments
        print("\n⚡ Step 3: Waiting for task assignments...")
        
        assignments = await demo.wait_for_assignments(len(created_tasks), timeout=30)
        
        # Step 4: Show distribution statistics
        print("\n📊 Step 4: Distribution statistics...")
        
        stats = await demo.get_distribution_stats()
        if stats:
            print(f"Total Tasks: {stats['total_tasks']}")
            print(f"Active Executors: {stats['total_executors']}")
            print(f"MAE Fairness: {stats.get('mae', 'N/A')}")
            
            print("\nExecutor Utilization:")
            for assignment in stats['assignments']:
                utilization_pct = assignment['utilization'] * 100
                print(f"  {assignment['name']}: {assignment['assigned_today']}/{assignment['daily_limit']} ({utilization_pct:.1f}%)")
        
        # Step 5: Show recent assignments
        print("\n📋 Step 5: Recent assignments...")
        
        if assignments:
            print(f"Found {len(assignments)} recent assignments:")
            for assignment in assignments[:10]:  # Show first 10
                print(f"  Task {assignment['task_id']} → {assignment['executor_name']} (Score: {assignment.get('score', 'N/A')})")
        
        # Step 6: Performance summary
        print("\n🎯 Demo Summary:")
        print(f"✅ Created {len(created_executors)} executors")
        print(f"✅ Created {len(created_tasks)} tasks")
        print(f"✅ Processed {len(assignments)} assignments")
        
        if stats and stats.get('mae'):
            mae = float(stats['mae'])
            if mae < 0.1:
                print("🎉 Excellent fairness distribution!")
            elif mae < 0.2:
                print("✅ Good fairness distribution")
            else:
                print("⚠️  Fairness could be improved")
        
        print("\n🎉 Demo completed successfully!")
        print("\n💡 Next steps:")
        print("   - Open http://localhost:8501 for the Streamlit dashboard")
        print("   - Check http://localhost:9090 for Prometheus metrics")
        print("   - View API docs at http://localhost:8000/docs")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
