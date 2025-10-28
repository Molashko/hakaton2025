from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from typing import Dict, Any

# Metrics definitions
assignments_total = Counter(
    'assignments_total',
    'Total number of task assignments',
    ['executor_id', 'status']
)

assignment_latency = Histogram(
    'assignment_latency_seconds',
    'Time taken to assign a task',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

mae_fairness = Gauge(
    'mae_fairness',
    'Mean Absolute Error for fairness distribution'
)

queue_lag = Gauge(
    'queue_lag',
    'Number of unprocessed tasks in queue'
)

executor_utilization = Gauge(
    'executor_utilization',
    'Current utilization of executor',
    ['executor_id', 'executor_name']
)

active_executors = Gauge(
    'active_executors_total',
    'Total number of active executors'
)

class MetricsCollector:
    def __init__(self, port: int = 8001):
        self.port = port
        self.server_started = False
    
    def start_server(self):
        """Start Prometheus metrics server"""
        if not self.server_started:
            start_http_server(self.port)
            self.server_started = True
            print(f"Prometheus metrics server started on port {self.port}")
    
    def record_assignment(self, executor_id: int, executor_name: str, status: str, latency: float):
        """Record assignment metrics"""
        assignments_total.labels(
            executor_id=str(executor_id),
            status=status
        ).inc()
        
        assignment_latency.observe(latency)
    
    def update_fairness_mae(self, mae: float):
        """Update fairness MAE metric"""
        mae_fairness.set(mae)
    
    def update_queue_lag(self, lag: int):
        """Update queue lag metric"""
        queue_lag.set(lag)
    
    def update_executor_utilization(self, executor_id: int, executor_name: str, utilization: float):
        """Update executor utilization metric"""
        executor_utilization.labels(
            executor_id=str(executor_id),
            executor_name=executor_name
        ).set(utilization)
    
    def update_active_executors(self, count: int):
        """Update active executors count"""
        active_executors.set(count)

# Global metrics collector instance
metrics_collector = MetricsCollector()
