#!/usr/bin/env python3
"""
System health check script for Executor Balancer
Verifies all components are working correctly
"""

import asyncio
import aiohttp
import redis.asyncio as redis
import asyncpg
import sys
import os
from datetime import datetime

class HealthChecker:
    def __init__(self):
        self.results = {}
    
    async def check_api(self):
        """Check API health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8000/v1/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results['api'] = {
                            'status': 'healthy',
                            'version': data.get('version'),
                            'timestamp': data.get('timestamp')
                        }
                        return True
                    else:
                        self.results['api'] = {'status': 'unhealthy', 'error': f'HTTP {response.status}'}
                        return False
        except Exception as e:
            self.results['api'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_database(self):
        """Check PostgreSQL connection"""
        try:
            conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/executor_balancer")
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            
            if result == 1:
                self.results['database'] = {'status': 'healthy'}
                return True
            else:
                self.results['database'] = {'status': 'unhealthy', 'error': 'Unexpected result'}
                return False
        except Exception as e:
            self.results['database'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_redis(self):
        """Check Redis connection"""
        try:
            r = redis.from_url("redis://localhost:6379/0")
            result = await r.ping()
            await r.close()
            
            if result:
                self.results['redis'] = {'status': 'healthy'}
                return True
            else:
                self.results['redis'] = {'status': 'unhealthy', 'error': 'Ping failed'}
                return False
        except Exception as e:
            self.results['redis'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_streamlit(self):
        """Check Streamlit dashboard"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8501", timeout=5) as response:
                    if response.status == 200:
                        self.results['streamlit'] = {'status': 'healthy'}
                        return True
                    else:
                        self.results['streamlit'] = {'status': 'unhealthy', 'error': f'HTTP {response.status}'}
                        return False
        except Exception as e:
            self.results['streamlit'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_prometheus(self):
        """Check Prometheus metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:9090", timeout=5) as response:
                    if response.status == 200:
                        self.results['prometheus'] = {'status': 'healthy'}
                        return True
                    else:
                        self.results['prometheus'] = {'status': 'unhealthy', 'error': f'HTTP {response.status}'}
                        return False
        except Exception as e:
            self.results['prometheus'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_metrics_endpoint(self):
        """Check Prometheus metrics endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8001/metrics", timeout=5) as response:
                    if response.status == 200:
                        content = await response.text()
                        if 'assignments_total' in content:
                            self.results['metrics'] = {'status': 'healthy', 'metrics_found': True}
                            return True
                        else:
                            self.results['metrics'] = {'status': 'unhealthy', 'error': 'No metrics found'}
                            return False
                    else:
                        self.results['metrics'] = {'status': 'unhealthy', 'error': f'HTTP {response.status}'}
                        return False
        except Exception as e:
            self.results['metrics'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def check_worker_queue(self):
        """Check if worker is processing tasks"""
        try:
            r = redis.from_url("redis://localhost:6379/0")
            stream_length = await r.xlen("task_queue")
            await r.close()
            
            self.results['worker_queue'] = {
                'status': 'healthy',
                'queue_length': stream_length
            }
            return True
        except Exception as e:
            self.results['worker_queue'] = {'status': 'unhealthy', 'error': str(e)}
            return False
    
    async def run_all_checks(self):
        """Run all health checks"""
        print("🔍 Executor Balancer Health Check")
        print("=" * 50)
        
        checks = [
            ("API Server", self.check_api),
            ("PostgreSQL Database", self.check_database),
            ("Redis Cache", self.check_redis),
            ("Streamlit Dashboard", self.check_streamlit),
            ("Prometheus Server", self.check_prometheus),
            ("Metrics Endpoint", self.check_metrics_endpoint),
            ("Worker Queue", self.check_worker_queue)
        ]
        
        passed = 0
        total = len(checks)
        
        for name, check_func in checks:
            print(f"\n🔍 Checking {name}...")
            try:
                result = await check_func()
                if result:
                    print(f"✅ {name}: OK")
                    passed += 1
                else:
                    print(f"❌ {name}: FAILED")
            except Exception as e:
                print(f"❌ {name}: ERROR - {e}")
        
        print("\n" + "=" * 50)
        print(f"📊 Health Check Summary: {passed}/{total} services healthy")
        
        if passed == total:
            print("🎉 All systems operational!")
            return True
        else:
            print("⚠️  Some services need attention")
            return False
    
    def print_detailed_results(self):
        """Print detailed health check results"""
        print("\n📋 Detailed Results:")
        print("-" * 30)
        
        for service, result in self.results.items():
            status = result['status']
            if status == 'healthy':
                print(f"✅ {service.upper()}: {status}")
                if 'version' in result:
                    print(f"   Version: {result['version']}")
                if 'queue_length' in result:
                    print(f"   Queue Length: {result['queue_length']}")
            else:
                print(f"❌ {service.upper()}: {status}")
                if 'error' in result:
                    print(f"   Error: {result['error']}")

async def main():
    """Main health check function"""
    checker = HealthChecker()
    
    try:
        success = await checker.run_all_checks()
        checker.print_detailed_results()
        
        if success:
            print("\n🚀 System is ready for use!")
            print("\n📱 Available interfaces:")
            print("   - API: http://localhost:8000")
            print("   - API Docs: http://localhost:8000/docs")
            print("   - Dashboard: http://localhost:8501")
            print("   - Metrics: http://localhost:9090")
            sys.exit(0)
        else:
            print("\n🔧 Please check the failed services and try again")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
