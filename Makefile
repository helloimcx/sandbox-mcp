# Makefile for Python Sandbox MCP Server
# Test-Driven Development (TDD) Workflow

.PHONY: help install install-dev test test-unit test-integration test-e2e test-watch test-coverage test-fast test-performance test-benchmark test-memory test-load test-profile lint format clean run docker-build docker-run setup-tdd

# Default target
help:
	@echo "Sandbox MCP Server - TDD Development Workflow"
	@echo ""
	@echo "Available targets:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  setup-tdd    - Setup TDD environment"
	@echo ""
	@echo "Testing (TDD Workflow):"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-e2e     - Run end-to-end tests only"
	@echo "  test-watch   - Run tests in watch mode (TDD)"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-fast    - Run fast tests (exclude slow)"
	@echo ""
	@echo "Performance Testing:"
	@echo "  test-performance - Run all performance tests"
	@echo "  test-benchmark   - Run benchmark tests"
	@echo "  test-memory      - Run memory performance tests"
	@echo "  test-load        - Run load tests (requires server)"
	@echo "  test-profile     - Run profiling tests"
	@echo ""
	@echo "  clean        - Clean up temporary files"
	@echo "  run          - Run the server"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run   - Run with Docker"
	@echo "  example      - Run client example"

# Installation targets
install:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv sync --no-dev; \
	else \
		echo "Installing with pip..."; \
		pip install -r requirements.txt; \
	fi

install-dev:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv (dev)..."; \
		uv sync; \
	else \
		echo "Installing with pip (dev)..."; \
		pip install -r requirements-dev.txt; \
	fi

# TDD Setup
setup-tdd:
	@echo "Setting up TDD environment..."
	mkdir -p tests/logs
	mkdir -p tests/reports
	mkdir -p htmlcov
	@echo "✅ TDD environment ready"

# Testing - TDD Workflow
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🔬 Running unit tests (TDD Red-Green-Refactor)..."
	pytest tests/unit/ -v

test-integration:
	@echo "🔗 Running integration tests..."
	pytest tests/integration/ -v

test-e2e:
	@echo "🌐 Running end-to-end tests..."
	pytest tests/e2e/ -v -s

test-fast:
	@echo "⚡ Running fast tests (exclude slow)..."
	pytest -m "not slow" -v

test-coverage:
	@echo "📊 Running tests with coverage..."
	pytest tests/ -v --cov=src/sandbox_mcp --cov-report=html --cov-report=term-missing
	@echo "📈 Coverage report: htmlcov/index.html"

test-cov: test-coverage

test-watch:
	@echo "👀 Starting TDD watch mode..."
	@echo "Press Ctrl+C to stop"
	@command -v ptw >/dev/null 2>&1 || pip install pytest-watch
	ptw --runner "pytest tests/unit/ -v"

# TDD Workflow helpers
tdd-red:
	@echo "🔴 TDD Red Phase: Write failing test"
	@echo "1. Write a failing test for new functionality"
	@echo "2. Run: make test-unit"
	@echo "3. Verify the test fails as expected"

tdd-green:
	@echo "🟢 TDD Green Phase: Make test pass"
	@echo "1. Write minimal code to make the test pass"
	@echo "2. Run: make test-unit"
	@echo "3. Verify all tests pass"

tdd-refactor:
	@echo "🔵 TDD Refactor Phase: Improve code"
	@echo "1. Refactor code while keeping tests green"
	@echo "2. Run: make test-unit"
	@echo "3. Ensure all tests still pass"

# Code quality
lint:
	@echo "🔍 Running linting checks..."
	flake8 src/ tests/
	mypy src/
	@echo "✅ Linting complete"

format:
	@echo "🎨 Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "✅ Code formatted"
	black src/ tests/ examples/
	isort src/ tests/ examples/

format-check:
	black --check src/ tests/ examples/
	isort --check-only src/ tests/ examples/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

# Running
run:
	python run.py

run-dev:
	python run.py --debug

run-with-auth:
	python run.py --api-key secret123

# Docker
docker-build:
	docker build -t sandbox-mcp .

docker-run:
	docker run -p 16010:16010 sandbox-mcp

docker-compose-up:
	docker-compose up --build

docker-compose-down:
	docker-compose down

# Examples
example:
	python examples/client_example.py

# Development workflow
dev-setup: install-dev
	@echo "Development environment ready!"
	@echo "Run 'make run-dev' to start the server in debug mode"

ci: format-check lint test
	@echo "All CI checks passed!"

# Quick start
quick-start: install run

# Performance Testing
test-performance:
	@echo "🚀 Running all performance tests..."
	python scripts/run_performance_tests.py --type all

test-benchmark:
	@echo "⏱️  Running benchmark tests..."
	python scripts/run_performance_tests.py --type benchmark

test-memory:
	@echo "🧠 Running memory performance tests..."
	python scripts/run_performance_tests.py --type memory

test-load:
	@echo "📈 Running load tests..."
	@echo "⚠️  Make sure the server is running: make run"
	python scripts/run_performance_tests.py --type load

test-load-quick:
	@echo "📈 Running quick load tests (30s, 5 users)..."
	python scripts/run_performance_tests.py --type load --duration 30 --users 5

test-load-heavy:
	@echo "📈 Running heavy load tests (300s, 50 users)..."
	python scripts/run_performance_tests.py --type load --duration 300 --users 50

test-profile:
	@echo "🔍 Running profiling tests..."
	python scripts/run_performance_tests.py --type profile

perf-install:
	@echo "📦 Installing performance testing dependencies..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv sync --group dev; \
	else \
		echo "Installing with pip..."; \
		pip install pytest-benchmark>=4.0.0 locust>=2.17.0 memory-profiler>=0.61.0; \
	fi
	@echo "✅ Performance testing dependencies installed"

perf-report:
	@echo "📊 Generating performance report..."
	python scripts/run_performance_tests.py --type benchmark --no-report
	@echo "📈 Performance report available at: tests/reports/performance_report.html"

# Performance testing workflow
perf-setup: perf-install
	@echo "🚀 Performance testing environment ready!"
	@echo "Run 'make test-performance' to run all performance tests"

perf-ci: test-benchmark test-memory
	@echo "✅ Performance CI checks completed!"

# Show project info
info:
	@echo "Python Sandbox MCP Server"
	@echo "========================"
