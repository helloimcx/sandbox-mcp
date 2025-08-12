"""Locust load testing configuration for the sandbox MCP server."""

from locust import HttpUser, task, between
import json
import random
import string


class SandboxMCPUser(HttpUser):
    """Simulated user for load testing the sandbox MCP server."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts. Create a session."""
        self.session_id = self.generate_session_id()
        self.create_session()
    
    def on_stop(self):
        """Called when a user stops. Clean up session."""
        self.delete_session()
    
    def generate_session_id(self):
        """Generate a random session ID."""
        return 'load-test-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    def create_session(self):
        """Create a new session."""
        response = self.client.post(
            "/sessions",
            json={"session_id": self.session_id},
            name="Create Session"
        )
        if response.status_code != 200:
            print(f"Failed to create session: {response.status_code}")
    
    def delete_session(self):
        """Delete the session."""
        self.client.delete(
            f"/sessions/{self.session_id}",
            name="Delete Session"
        )
    
    @task(10)
    def health_check(self):
        """Check server health."""
        self.client.get("/health", name="Health Check")
    
    @task(5)
    def get_session_info(self):
        """Get session information."""
        self.client.get(
            f"/sessions/{self.session_id}",
            name="Get Session Info"
        )
    
    @task(20)
    def execute_simple_code(self):
        """Execute simple Python code."""
        codes = [
            "print('Hello, World!')",
            "x = 1 + 1\nprint(x)",
            "import math\nprint(math.pi)",
            "for i in range(5):\n    print(i)",
            "result = sum([1, 2, 3, 4, 5])\nprint(result)"
        ]
        
        code = random.choice(codes)
        self.client.post(
            f"/sessions/{self.session_id}/execute",
            json={"code": code},
            name="Execute Simple Code"
        )
    
    @task(10)
    def execute_math_operations(self):
        """Execute mathematical operations."""
        operations = [
            "import numpy as np\narr = np.array([1, 2, 3, 4, 5])\nprint(arr.mean())",
            "import pandas as pd\ndf = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})\nprint(df.sum())",
            "import matplotlib.pyplot as plt\nplt.plot([1, 2, 3, 4])\nplt.savefig('test.png')\nprint('Plot saved')",
            "result = sum(i**2 for i in range(100))\nprint(result)",
            "factorial = 1\nfor i in range(1, 11):\n    factorial *= i\nprint(factorial)"
        ]
        
        code = random.choice(operations)
        self.client.post(
            f"/sessions/{self.session_id}/execute",
            json={"code": code},
            name="Execute Math Operations"
        )
    
    @task(5)
    def execute_data_processing(self):
        """Execute data processing code."""
        data_codes = [
            """import pandas as pd
data = {'name': ['Alice', 'Bob', 'Charlie'], 'age': [25, 30, 35]}
df = pd.DataFrame(data)
print(df.describe())""",
            """import json
data = {'key1': 'value1', 'key2': [1, 2, 3]}
json_str = json.dumps(data)
print(json_str)""",
            """import csv
import io
data = [['name', 'age'], ['Alice', 25], ['Bob', 30]]
output = io.StringIO()
writer = csv.writer(output)
writer.writerows(data)
print(output.getvalue())"""
        ]
        
        code = random.choice(data_codes)
        self.client.post(
            f"/sessions/{self.session_id}/execute",
            json={"code": code},
            name="Execute Data Processing"
        )
    
    @task(3)
    def execute_long_running_code(self):
        """Execute longer running code."""
        long_codes = [
            """import time
for i in range(10):
    print(f'Step {i}')
    time.sleep(0.1)
print('Completed')""",
            """result = []
for i in range(1000):
    result.append(i ** 2)
print(f'Computed {len(result)} squares')""",
            """import random
data = [random.randint(1, 100) for _ in range(1000)]
sorted_data = sorted(data)
print(f'Sorted {len(sorted_data)} numbers')"""
        ]
        
        code = random.choice(long_codes)
        self.client.post(
            f"/sessions/{self.session_id}/execute",
            json={"code": code},
            name="Execute Long Running Code"
        )
    
    @task(2)
    def execute_error_code(self):
        """Execute code that produces errors (to test error handling)."""
        error_codes = [
            "undefined_variable",
            "1 / 0",
            "import non_existent_module",
            "[1, 2, 3][10]",
            "int('not_a_number')"
        ]
        
        code = random.choice(error_codes)
        self.client.post(
            f"/sessions/{self.session_id}/execute",
            json={"code": code},
            name="Execute Error Code"
        )


class AdminUser(HttpUser):
    """Admin user for testing administrative endpoints."""
    
    wait_time = between(5, 10)  # Longer wait time for admin operations
    weight = 1  # Lower weight compared to regular users
    
    @task(5)
    def health_check(self):
        """Check server health."""
        self.client.get("/health", name="Admin Health Check")
    
    @task(3)
    def list_all_sessions(self):
        """List all active sessions (if endpoint exists)."""
        self.client.get("/sessions", name="List All Sessions")
    
    @task(2)
    def cleanup_sessions(self):
        """Trigger session cleanup (if endpoint exists)."""
        self.client.post("/admin/cleanup", name="Cleanup Sessions")
    
    @task(1)
    def get_server_stats(self):
        """Get server statistics (if endpoint exists)."""
        self.client.get("/admin/stats", name="Get Server Stats")


class HeavyUser(HttpUser):
    """Heavy user that creates multiple sessions and executes complex code."""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight for heavy users
    
    def on_start(self):
        """Create multiple sessions."""
        self.session_ids = []
        for i in range(3):  # Create 3 sessions per heavy user
            session_id = f'heavy-user-{self.generate_session_id()}-{i}'
            self.session_ids.append(session_id)
            self.client.post(
                "/sessions",
                json={"session_id": session_id},
                name="Heavy User Create Session"
            )
    
    def on_stop(self):
        """Clean up all sessions."""
        for session_id in self.session_ids:
            self.client.delete(
                f"/sessions/{session_id}",
                name="Heavy User Delete Session"
            )
    
    def generate_session_id(self):
        """Generate a random session ID."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    @task(10)
    def execute_complex_code(self):
        """Execute complex code across multiple sessions."""
        session_id = random.choice(self.session_ids)
        
        complex_codes = [
            """import numpy as np
import pandas as pd

# Create large dataset
data = np.random.randn(1000, 10)
df = pd.DataFrame(data)

# Perform operations
result = df.groupby(df.columns[0] > 0).mean()
print(f'Processed {len(df)} rows')
print(result.head())""",
            """import matplotlib.pyplot as plt
import numpy as np

# Generate data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.savefig('complex_plot.png')
print('Complex plot generated')""",
            """# Fibonacci sequence calculation
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

results = [fibonacci(i) for i in range(20)]
print(f'Fibonacci sequence: {results}')"""
        ]
        
        code = random.choice(complex_codes)
        self.client.post(
            f"/sessions/{session_id}/execute",
            json={"code": code},
            name="Heavy User Execute Complex Code"
        )