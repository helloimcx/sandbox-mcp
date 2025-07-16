# Makefile for Python Sandbox MCP Server

.PHONY: help install install-dev test lint format clean run docker-build docker-run

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code"
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

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/sandbox_mcp --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
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
	docker run -p 8000:8000 sandbox-mcp

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

# Show project info
info:
	@echo "Python Sandbox MCP Server"
	@echo "========================"
	@python -c "import sys; print(f'Python: {sys.version}')"
	@echo "Project structure:"
	@find src/ -name "*.py" | head -10
	@echo "..."