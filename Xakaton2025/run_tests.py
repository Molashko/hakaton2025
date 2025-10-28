#!/usr/bin/env python3
"""
Test runner script for Executor Balancer
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Executor Balancer Tests")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("app"):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install dependencies if needed
    if not os.path.exists("venv"):
        print("📦 Creating virtual environment...")
        run_command("python -m venv venv", "Creating virtual environment")
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix/Linux/MacOS
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    # Install dependencies
    run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies")
    
    # Run linting
    run_command(f"{pip_cmd} install flake8 black isort", "Installing linting tools")
    
    print("\n🔍 Running code quality checks...")
    run_command(f"{pip_cmd} run flake8 app/ tests/", "Flake8 linting")
    run_command(f"{pip_cmd} run black --check app/ tests/", "Black formatting check")
    run_command(f"{pip_cmd} run isort --check-only app/ tests/", "Import sorting check")
    
    # Run tests
    print("\n🧪 Running tests...")
    success = run_command(f"{pip_cmd} run pytest tests/ -v --tb=short", "Running pytest")
    
    if success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
