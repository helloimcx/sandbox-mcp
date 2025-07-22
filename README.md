# Python Sandbox MCP Server

A secure Python code execution sandbox with Model Context Protocol (MCP) support, designed for remote code execution with proper isolation and resource management.

## Features

- 🔒 **Secure Execution**: Isolated Python kernel execution environment
- 🚀 **High Performance**: Async/await support with efficient resource management
- 📡 **Streaming Results**: Real-time code execution results via Server-Sent Events
- 🔄 **Session Management**: Persistent kernel sessions with automatic cleanup
- 🐳 **Docker Ready**: Full containerization support for easy deployment
- 🔑 **Authentication**: Optional API key authentication
- 📊 **Monitoring**: Health checks and session monitoring endpoints
- ⚡ **Resource Limits**: Configurable execution timeouts and memory limits

## Quick Start

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd python-sandbox-mcp

# Install dependencies with uv
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Start the server
python -m main
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t sandbox-mcp .
docker run -p 16010:16010 sandbox-mcp
```

## Configuration

Configure the server using environment variables or a `.env` file:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
vim .env
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `16010` | Server port |
| `DEBUG` | `false` | Enable debug mode |
| `API_KEY` | `None` | API key for authentication (optional) |
| `MAX_KERNELS` | `10` | Maximum concurrent kernels |
| `KERNEL_TIMEOUT` | `300` | Kernel idle timeout (seconds) |
| `MAX_EXECUTION_TIME` | `30` | Maximum execution time per request |
| `MAX_MEMORY_MB` | `512` | Memory limit per kernel |

## API Usage

### Execute Code

```bash
curl -X POST "http://localhost:16010/api/v1/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "print('Hello, World!')\nimport matplotlib.pyplot as plt\nplt.plot([1,2,3], [1,4,9])\nplt.show()",
    "session_id": "my-session"
  }'
```

### With API Key Authentication

```bash
curl -X POST "http://localhost:16010/api/v1/execute" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{"code": "print('Hello, World!')"}'
```

### List Active Sessions

```bash
curl "http://localhost:16010/api/v1/sessions"
```

### Health Check

```bash
curl "http://localhost:16010/api/v1/health"
```

## Response Format

The server returns streaming NDJSON responses with different message types:

### Text Output
```json
{"text": "Hello, World!\n"}
```

### Image Output
```json
{
  "image": "iVBORw0KGgoAAAANSUhEUgAA...",
  "format": "png"
}
```

### Error Output
```json
{
  "error": "NameError: name 'undefined_var' is not defined",
  "traceback": ["Traceback (most recent call last):", "..."]
}
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv sync --group dev

# Run tests
pytest

# Code formatting
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

### Project Structure

```
src/sandbox_mcp/
├── __init__.py          # Package initialization
├── main.py              # FastAPI application
├── api.py               # API routes and handlers
├── models.py            # Pydantic data models
├── config.py            # Configuration management
├── kernel_manager.py    # Jupyter kernel management
└── cli.py               # Command line interface
```

## Deployment

### Production Docker Deployment

```bash
# Use production profile with nginx
docker-compose --profile production up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sandbox-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sandbox-mcp
  template:
    metadata:
      labels:
        app: sandbox-mcp
    spec:
      containers:
      - name: sandbox-mcp
        image: sandbox-mcp:latest
        ports:
        - containerPort: 16010
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: sandbox-mcp-secret
              key: api-key
        resources:
          limits:
            memory: "1Gi"
            cpu: "1000m"
          requests:
            memory: "512Mi"
            cpu: "500m"
```

## Security Considerations

1. **API Key Authentication**: Always use API key authentication in production
2. **Network Isolation**: Run in isolated network environments
3. **Resource Limits**: Configure appropriate memory and CPU limits
4. **Input Validation**: The server validates all input, but additional validation may be needed
5. **Logging**: Monitor execution logs for suspicious activity

## Monitoring

### Health Checks

The server provides health check endpoints for monitoring:

- `GET /api/v1/health` - Basic health status
- `GET /api/v1/sessions` - Active session information

### Metrics

For production monitoring, consider integrating with:

- Prometheus for metrics collection
- Grafana for visualization
- ELK stack for log analysis

## Troubleshooting

### Common Issues

1. **Kernel startup failures**: Check system resources and dependencies
2. **Memory issues**: Adjust `MAX_MEMORY_MB` setting
3. **Timeout errors**: Increase `MAX_EXECUTION_TIME` for long-running code
4. **Port conflicts**: Change the `PORT` setting

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
python -m main
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the [Issues](../../issues) page
2. Review the documentation
3. Create a new issue with detailed information