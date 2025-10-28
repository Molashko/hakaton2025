import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.database import AsyncSessionLocal
from app.models import Executor, Task, Assignment
from app.services.matcher import MatcherService
from app.rule_engine import RuleEngine

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    """Create a test database session."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client():
    """Create a test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def sample_executor(db_session: AsyncSession):
    """Create a sample executor for testing."""
    executor = Executor(
        name="Test Executor",
        parameters={"skills": ["python", "fastapi"]},
        active=True,
        daily_limit=100,
        assigned_today=0
    )
    db_session.add(executor)
    await db_session.commit()
    await db_session.refresh(executor)
    return executor

@pytest.fixture
async def sample_task(db_session: AsyncSession):
    """Create a sample task for testing."""
    task = Task(
        external_id="TEST_TASK_001",
        parameters={"priority": "high", "category": "test"},
        weight=1,
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task

class TestRuleEngine:
    """Test Rule Engine functionality."""
    
    def test_eq_operator(self):
        """Test equality operator."""
        engine = RuleEngine()
        rule = {
            "operator": "eq",
            "field": "task.priority",
            "value": "high"
        }
        context = {
            "task": {"priority": "high"}
        }
        assert engine.evaluate(rule, context) == True
        
        context = {
            "task": {"priority": "low"}
        }
        assert engine.evaluate(rule, context) == False
    
    def test_gt_operator(self):
        """Test greater than operator."""
        engine = RuleEngine()
        rule = {
            "operator": "gt",
            "field": "executor.assigned_today",
            "value": 10
        }
        context = {
            "executor": {"assigned_today": 15}
        }
        assert engine.evaluate(rule, context) == True
        
        context = {
            "executor": {"assigned_today": 5}
        }
        assert engine.evaluate(rule, context) == False
    
    def test_in_operator(self):
        """Test in operator."""
        engine = RuleEngine()
        rule = {
            "operator": "in",
            "field": "executor.skills",
            "value": ["python", "fastapi"]
        }
        context = {
            "executor": {"skills": ["python", "django"]}
        }
        assert engine.evaluate(rule, context) == True
        
        context = {
            "executor": {"skills": ["java", "spring"]}
        }
        assert engine.evaluate(rule, context) == False
    
    def test_and_operator(self):
        """Test AND operator."""
        engine = RuleEngine()
        rule = {
            "operator": "and",
            "conditions": [
                {
                    "operator": "eq",
                    "field": "task.priority",
                    "value": "high"
                },
                {
                    "operator": "lt",
                    "field": "executor.assigned_today",
                    "value": 50
                }
            ]
        }
        context = {
            "task": {"priority": "high"},
            "executor": {"assigned_today": 30}
        }
        assert engine.evaluate(rule, context) == True
        
        context = {
            "task": {"priority": "low"},
            "executor": {"assigned_today": 30}
        }
        assert engine.evaluate(rule, context) == False
    
    def test_weight_calculation(self):
        """Test weight calculation."""
        engine = RuleEngine()
        weight_rules = [
            {
                "condition": {
                    "operator": "eq",
                    "field": "task.priority",
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
            }
        ]
        
        context = {
            "task": {"priority": "high"},
            "executor": {"assigned_today": 15}
        }
        
        weight = engine.calculate_weight(weight_rules, context)
        assert weight == 3.0  # 2.0 * 1.5
        
        context = {
            "task": {"priority": "low"},
            "executor": {"assigned_today": 15}
        }
        
        weight = engine.calculate_weight(weight_rules, context)
        assert weight == 1.5  # Only second condition matches

class TestMatcherService:
    """Test Matcher Service functionality."""
    
    @pytest.mark.asyncio
    async def test_find_best_executor(self, db_session: AsyncSession, sample_task: Task):
        """Test finding best executor for a task."""
        # Create test executors
        executor1 = Executor(
            name="Executor 1",
            parameters={"skills": ["python"]},
            active=True,
            daily_limit=100,
            assigned_today=20
        )
        executor2 = Executor(
            name="Executor 2",
            parameters={"skills": ["java"]},
            active=True,
            daily_limit=100,
            assigned_today=80
        )
        
        db_session.add_all([executor1, executor2])
        await db_session.commit()
        
        matcher = MatcherService(db_session)
        result = await matcher.find_best_executor(sample_task)
        
        assert result is not None
        executor, score = result
        # Should prefer executor with lower utilization
        assert executor.name == "Executor 1"
        assert score > 0
    
    @pytest.mark.asyncio
    async def test_assign_task(self, db_session: AsyncSession, sample_task: Task):
        """Test task assignment."""
        executor = Executor(
            name="Test Executor",
            active=True,
            daily_limit=100,
            assigned_today=0
        )
        db_session.add(executor)
        await db_session.commit()
        await db_session.refresh(executor)
        
        matcher = MatcherService(db_session)
        assignment = await matcher.assign_task(sample_task)
        
        assert assignment is not None
        assert assignment.task_id == sample_task.id
        assert assignment.executor_id == executor.id
        assert sample_task.status == "assigned"
        assert executor.assigned_today == 1
    
    @pytest.mark.asyncio
    async def test_no_available_executor(self, db_session: AsyncSession):
        """Test when no executor is available."""
        task = Task(
            external_id="TEST_NO_EXECUTOR",
            status="pending"
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        matcher = MatcherService(db_session)
        assignment = await matcher.assign_task(task)
        
        assert assignment is None
        assert task.status == "pending"

class TestAPIEndpoints:
    """Test API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient):
        """Test creating a task via API."""
        task_data = {
            "external_id": "API_TEST_001",
            "parameters": {"priority": "high"},
            "weight": 1
        }
        
        response = await client.post("/v1/tasks", json=task_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] > 0
    
    @pytest.mark.asyncio
    async def test_create_executor(self, client: AsyncClient):
        """Test creating an executor via API."""
        executor_data = {
            "name": "API Test Executor",
            "parameters": {"skills": ["python"]},
            "active": True,
            "daily_limit": 100
        }
        
        response = await client.post("/v1/executors", json=executor_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "API Test Executor"
        assert data["active"] == True
        assert data["daily_limit"] == 100
    
    @pytest.mark.asyncio
    async def test_get_executors(self, client: AsyncClient):
        """Test getting executors via API."""
        response = await client.get("/v1/executors")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

if __name__ == "__main__":
    pytest.main([__file__])
