#!/bin/bash

# Run tests for tool-call-sandbox

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Tool Call Sandbox Test Suite ==="
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install -q -r requirements.txt
pip install -q pytest pytest-cov httpx

echo ""
echo "Running tests..."
echo ""

# Run tests with different options based on arguments
case "${1:-all}" in
    unit)
        echo "Running unit tests only (no Docker required)..."
        pytest tests/test_tool_loader.py tests/test_api.py -v --tb=short
        ;;
    integration)
        echo "Running integration tests (requires Docker and sandbox image)..."
        pytest tests/test_executor.py -v --tb=short -m "not slow"
        ;;
    all)
        echo "Running all tests..."
        pytest tests/ -v --tb=short
        ;;
    coverage)
        echo "Running tests with coverage..."
        pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
        echo ""
        echo "Coverage report generated in htmlcov/"
        ;;
    *)
        echo "Usage: $0 [unit|integration|all|coverage]"
        echo ""
        echo "  unit        - Run unit tests only (no Docker required)"
        echo "  integration - Run integration tests (requires Docker)"
        echo "  all         - Run all tests (default)"
        echo "  coverage    - Run all tests with coverage report"
        exit 1
        ;;
esac

echo ""
echo "Tests completed!"
