# Multi-stage build for Python Sandbox MCP Server
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock* .
COPY README.md .

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.13-slim AS production

# Install system dependencies for Jupyter
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user with home directory
RUN groupadd -r sandbox && useradd -r -g sandbox -m -d /home/sandbox sandbox

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ src/

# Set ownership
RUN chown -R sandbox:sandbox /app && chown -R sandbox:sandbox /home/sandbox

# Switch to non-root user
USER sandbox

# Initialize mplfonts for Chinese font support
RUN /app/.venv/bin/mplfonts init || echo "mplfonts init failed, continuing..."

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"


# Expose port
EXPOSE 16010

# Default command
CMD ["python", "-m", "main"]