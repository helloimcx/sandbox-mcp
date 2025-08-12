#!/usr/bin/env python3
"""Script to run performance tests for the sandbox MCP server."""

import argparse
import subprocess
import sys
import os
import time
from pathlib import Path
import json


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None


def install_dependencies():
    """Install performance testing dependencies."""
    print("Installing performance testing dependencies...")
    
    # Install using uv (as specified in project rules)
    cmd = ["uv", "sync", "--group", "dev"]
    result = run_command(cmd)
    
    if result is None:
        print("Failed to install dependencies")
        return False
    
    print("Dependencies installed successfully")
    return True


def run_benchmark_tests(test_pattern=None):
    """Run benchmark tests using pytest-benchmark."""
    print("Running benchmark tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/performance/",
        "-v",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-json=tests/reports/benchmark_results.json",
        "--benchmark-histogram=tests/reports/benchmark_histogram"
    ]
    
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    result = run_command(cmd)
    return result is not None


def run_memory_tests():
    """Run memory performance tests."""
    print("Running memory performance tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/performance/test_memory_performance.py",
        "-v",
        "-s",
        "--tb=short"
    ]
    
    result = run_command(cmd)
    return result is not None


def run_load_tests(duration=60, users=10, spawn_rate=2):
    """Run load tests using Locust."""
    print(f"Running load tests with {users} users for {duration} seconds...")
    
    # Check if server is running
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("Server is not responding properly. Please start the server first.")
            return False
    except requests.exceptions.RequestException:
        print("Server is not running. Please start the server first.")
        print("You can start the server with: python -m uvicorn src.main:app --host 0.0.0.0 --port 8000")
        return False
    
    # Run Locust
    cmd = [
        "locust",
        "-f", "tests/performance/locustfile.py",
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", f"{duration}s",
        "--host", "http://localhost:8000",
        "--html", "tests/reports/load_test_report.html",
        "--csv", "tests/reports/load_test"
    ]
    
    result = run_command(cmd)
    return result is not None


def run_profile_tests():
    """Run profiling tests to identify performance bottlenecks."""
    print("Running profiling tests...")
    
    # Run with cProfile
    cmd = [
        "python", "-m", "cProfile",
        "-o", "tests/reports/profile_results.prof",
        "-m", "pytest",
        "tests/performance/test_kernel_manager_performance.py::TestKernelManagerPerformance::test_session_creation_performance",
        "-v"
    ]
    
    result = run_command(cmd)
    
    if result:
        # Generate human-readable profile report
        cmd = [
            "python", "-c",
            "import pstats; p = pstats.Stats('tests/reports/profile_results.prof'); p.sort_stats('cumulative').print_stats(20)"
        ]
        run_command(cmd)
    
    return result is not None


def generate_performance_report():
    """Generate comprehensive performance report."""
    print("Generating performance report...")
    
    report_dir = Path("tests/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect all performance data
    performance_data = {
        "timestamp": time.time(),
        "test_run_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmark_results": None,
        "load_test_results": None,
        "memory_test_results": None
    }
    
    # Load benchmark results if available
    benchmark_file = report_dir / "benchmark_results.json"
    if benchmark_file.exists() and benchmark_file.stat().st_size > 0:
        try:
            with open(benchmark_file) as f:
                performance_data["benchmark_results"] = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            performance_data["benchmark_results"] = None
    
    # Load load test results if available
    load_test_file = report_dir / "load_test_stats.csv"
    if load_test_file.exists():
        performance_data["load_test_results"] = str(load_test_file)
    
    # Generate HTML report
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sandbox MCP Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 3px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .warning {{ color: orange; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Sandbox MCP Performance Report</h1>
        <p>Generated on: {performance_data['test_run_date']}</p>
    </div>
    
    <div class="section">
        <h2>Test Summary</h2>
        <div class="metric">Benchmark Tests: {'✓' if performance_data['benchmark_results'] else '✗'}</div>
        <div class="metric">Load Tests: {'✓' if performance_data['load_test_results'] else '✗'}</div>
        <div class="metric">Memory Tests: {'✓' if performance_data['memory_test_results'] else '✗'}</div>
    </div>
    
    <div class="section">
        <h2>Performance Metrics</h2>
        <p>Detailed performance metrics and recommendations will be displayed here.</p>
        <p>For detailed benchmark results, see: <a href="benchmark_results.json">benchmark_results.json</a></p>
        <p>For load test results, see: <a href="load_test_report.html">load_test_report.html</a></p>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <ul>
            <li>Monitor memory usage during high-load scenarios</li>
            <li>Optimize session creation and cleanup processes</li>
            <li>Consider implementing connection pooling for better performance</li>
            <li>Regular performance regression testing is recommended</li>
        </ul>
    </div>
</body>
</html>
"""
    
    # Save HTML report
    html_file = report_dir / "performance_report.html"
    with open(html_file, "w") as f:
        f.write(html_content)
    
    # Save JSON data
    json_file = report_dir / "performance_data.json"
    with open(json_file, "w") as f:
        json.dump(performance_data, f, indent=2)
    
    print(f"Performance report generated: {html_file}")
    print(f"Performance data saved: {json_file}")
    
    return True


def main():
    """Main function to run performance tests."""
    parser = argparse.ArgumentParser(description="Run performance tests for Sandbox MCP")
    parser.add_argument(
        "--type",
        choices=["all", "benchmark", "memory", "load", "profile"],
        default="all",
        help="Type of performance test to run"
    )
    parser.add_argument(
        "--pattern",
        help="Test pattern to match (for benchmark tests)"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of users for load testing"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration of load test in seconds"
    )
    parser.add_argument(
        "--spawn-rate",
        type=int,
        default=2,
        help="User spawn rate for load testing"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies before running tests"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating performance report"
    )
    
    args = parser.parse_args()
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    # Create reports directory
    reports_dir = Path("tests/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_dependencies():
            sys.exit(1)
    
    # Run tests based on type
    if args.type in ["all", "benchmark"]:
        if not run_benchmark_tests(args.pattern):
            success = False
    
    if args.type in ["all", "memory"]:
        if not run_memory_tests():
            success = False
    
    if args.type in ["all", "load"]:
        if not run_load_tests(args.duration, args.users, args.spawn_rate):
            success = False
    
    if args.type == "profile":
        if not run_profile_tests():
            success = False
    
    # Generate report
    if not args.no_report:
        generate_performance_report()
    
    if success:
        print("\n✅ Performance tests completed successfully!")
        print(f"📊 Reports available in: {reports_dir.absolute()}")
    else:
        print("\n❌ Some performance tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()