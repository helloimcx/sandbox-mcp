"""Performance test configuration and fixtures."""

import pytest
import asyncio
import time
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance tests."""
    return {
        'benchmark_rounds': 10,
        'benchmark_iterations': 100,
        'memory_threshold_mb': 100,
        'response_time_threshold_ms': 1000,
        'concurrent_users': 10,
        'load_test_duration': 60,  # seconds
    }


@pytest.fixture(scope="session")
def temp_test_dir():
    """Create temporary directory for performance tests."""
    temp_dir = tempfile.mkdtemp(prefix="perf_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def benchmark_config():
    """Configuration for pytest-benchmark."""
    return {
        'min_rounds': 5,
        'max_time': 10.0,
        'min_time': 0.1,
        'timer': time.perf_counter,
        'disable_gc': True,
        'warmup': True,
        'warmup_iterations': 3,
    }


@pytest.fixture
def memory_monitor():
    """Memory monitoring fixture."""
    import psutil
    
    class MemoryMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = self.get_memory_mb()
            self.peak_memory = self.initial_memory
            self.measurements = []
        
        def get_memory_mb(self):
            """Get current memory usage in MB."""
            return self.process.memory_info().rss / 1024 / 1024
        
        def record(self, label=""):
            """Record current memory usage."""
            current_memory = self.get_memory_mb()
            self.peak_memory = max(self.peak_memory, current_memory)
            self.measurements.append({
                'timestamp': time.time(),
                'memory_mb': current_memory,
                'label': label
            })
            return current_memory
        
        def get_increase(self):
            """Get memory increase from initial."""
            return self.get_memory_mb() - self.initial_memory
        
        def get_peak_increase(self):
            """Get peak memory increase from initial."""
            return self.peak_memory - self.initial_memory
        
        def assert_memory_limit(self, limit_mb):
            """Assert memory usage is within limit."""
            current_increase = self.get_increase()
            assert current_increase < limit_mb, f"Memory usage {current_increase:.2f}MB exceeds limit {limit_mb}MB"
    
    return MemoryMonitor()


@pytest.fixture
def performance_logger():
    """Performance logging fixture."""
    import logging
    
    # Create performance logger
    logger = logging.getLogger('performance')
    logger.setLevel(logging.INFO)
    
    # Create file handler for performance logs
    log_file = Path('tests/reports/performance.log')
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.FileHandler(log_file)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    yield logger
    
    # Clean up
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


@pytest.fixture
def async_benchmark():
    """Async benchmark fixture."""
    class AsyncBenchmark:
        def __init__(self):
            self.results = []
        
        async def run(self, async_func, rounds=10):
            """Run async function multiple times and measure performance."""
            times = []
            
            for _ in range(rounds):
                start_time = time.perf_counter()
                await async_func()
                end_time = time.perf_counter()
                times.append(end_time - start_time)
            
            result = {
                'min': min(times),
                'max': max(times),
                'mean': sum(times) / len(times),
                'rounds': rounds,
                'total_time': sum(times)
            }
            
            self.results.append(result)
            return result
    
    return AsyncBenchmark()


@pytest.fixture
def load_test_config():
    """Configuration for load testing."""
    return {
        'base_url': 'http://localhost:8000',
        'users': 10,
        'spawn_rate': 2,
        'run_time': '60s',
        'host': 'localhost:8000'
    }


@pytest.fixture(scope="session")
def performance_report_dir():
    """Create directory for performance reports."""
    report_dir = Path('tests/reports/performance')
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


@pytest.fixture
def benchmark_reporter(performance_report_dir):
    """Benchmark result reporter."""
    import json
    
    class BenchmarkReporter:
        def __init__(self, report_dir):
            self.report_dir = Path(report_dir)
            self.results = []
        
        def add_result(self, test_name, result):
            """Add benchmark result."""
            self.results.append({
                'test_name': test_name,
                'timestamp': time.time(),
                'result': result
            })
        
        def save_report(self, filename='benchmark_results.json'):
            """Save results to JSON file."""
            report_file = self.report_dir / filename
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            return report_file
        
        def generate_html_report(self):
            """Generate HTML report."""
            html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .pass { color: green; }
        .fail { color: red; }
    </style>
</head>
<body>
    <h1>Performance Test Results</h1>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Min Time (s)</th>
            <th>Max Time (s)</th>
            <th>Mean Time (s)</th>
            <th>Rounds</th>
            <th>Status</th>
        </tr>
"""
            
            for result in self.results:
                test_name = result['test_name']
                stats = result['result']
                
                # Determine status based on mean time
                status = 'pass' if stats.get('mean', 0) < 1.0 else 'fail'
                status_class = 'pass' if status == 'pass' else 'fail'
                
                html_content += f"""
        <tr>
            <td>{test_name}</td>
            <td>{stats.get('min', 0):.4f}</td>
            <td>{stats.get('max', 0):.4f}</td>
            <td>{stats.get('mean', 0):.4f}</td>
            <td>{stats.get('rounds', 0)}</td>
            <td class="{status_class}">{status.upper()}</td>
        </tr>"""
            
            html_content += """
    </table>
</body>
</html>"""
            
            html_file = self.report_dir / 'performance_report.html'
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            return html_file
    
    return BenchmarkReporter(performance_report_dir)


# Pytest configuration for performance tests
def pytest_configure(config):
    """Configure pytest for performance tests."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test"
    )
    config.addinivalue_line(
        "markers", "memory: mark test as a memory test"
    )
    config.addinivalue_line(
        "markers", "load: mark test as a load test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for performance tests."""
    for item in items:
        # Add performance marker to all tests in performance directory
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        
        # Add specific markers based on test name
        if "benchmark" in item.name:
            item.add_marker(pytest.mark.benchmark)
        if "memory" in item.name:
            item.add_marker(pytest.mark.memory)
        if "load" in item.name:
            item.add_marker(pytest.mark.load)


@pytest.fixture(autouse=True)
def disable_network_restrictions_for_performance():
    """Disable network restrictions for performance tests."""
    from unittest.mock import patch, AsyncMock, MagicMock
    from contextlib import asynccontextmanager
    
    # Mock all network restriction functions to do nothing
    def mock_apply_network_restrictions(*args, **kwargs):
        pass
    
    def mock_disable_network_access():
        pass
    
    def mock_enable_network_access(*args, **kwargs):
        pass
    
    def mock_restore_network_access():
        pass
    
    @asynccontextmanager
    async def mock_lifespan(app):
        # Do nothing during startup/shutdown to avoid network restrictions
        yield
    
    with patch('services.kernel_manager.kernel_manager') as mock_km, \
         patch('main.combined_lifespan', mock_lifespan), \
         patch('utils.network_restriction.apply_network_restrictions', mock_apply_network_restrictions), \
         patch('utils.network_restriction.disable_network_access', mock_disable_network_access), \
         patch('utils.network_restriction.enable_network_access', mock_enable_network_access), \
         patch('utils.network_restriction.restore_network_access', mock_restore_network_access):
        
        # Mock the kernel manager to prevent startup network restrictions
        mock_km.start = AsyncMock()
        mock_km.stop = AsyncMock()
        mock_km.sessions = {}
        
        yield


@pytest.fixture(autouse=True)
def performance_test_setup(request, performance_logger):
    """Setup for each performance test."""
    test_name = request.node.name
    performance_logger.info(f"Starting performance test: {test_name}")
    
    start_time = time.time()
    yield
    end_time = time.time()
    
    duration = end_time - start_time
    performance_logger.info(f"Completed performance test: {test_name} in {duration:.4f}s")