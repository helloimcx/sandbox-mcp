#!/usr/bin/env python3
"""Example client for the Python Sandbox MCP Server."""

import asyncio
import json
import aiohttp
from typing import AsyncGenerator, Dict, Any


class SandboxClient:
    """Client for interacting with the sandbox MCP server."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        url = f"{self.base_url}/api/v1/health"
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()
    
    async def execute_code(
        self, 
        code: str, 
        session_id: str = None,
        timeout: int = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute Python code and stream results."""
        url = f"{self.base_url}/api/v1/execute"
        payload = {"code": code}
        
        if session_id:
            payload["session_id"] = session_id
        if timeout:
            payload["timeout"] = timeout
        
        async with self.session.post(
            url, 
            json=payload, 
            headers=self._get_headers()
        ) as response:
            response.raise_for_status()
            
            async for line in response.content:
                if line.strip():
                    try:
                        yield json.loads(line.decode('utf-8'))
                    except json.JSONDecodeError:
                        continue
    
    async def list_sessions(self) -> Dict[str, Any]:
        """List active sessions."""
        url = f"{self.base_url}/api/v1/sessions"
        async with self.session.get(url, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()
    
    async def terminate_session(self, session_id: str) -> Dict[str, str]:
        """Terminate a session."""
        url = f"{self.base_url}/api/v1/sessions/{session_id}"
        async with self.session.delete(url, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()
    
    async def interrupt_session(self, session_id: str) -> Dict[str, str]:
        """Interrupt a session."""
        url = f"{self.base_url}/api/v1/sessions/{session_id}/interrupt"
        async with self.session.post(url, headers=self._get_headers()) as response:
            response.raise_for_status()
            return await response.json()


async def main():
    """Example usage of the sandbox client."""
    async with SandboxClient() as client:
        # Check server health
        print("Checking server health...")
        health = await client.health_check()
        print(f"Server status: {health['status']}")
        print(f"Version: {health['version']}")
        print(f"Active sessions: {health['active_sessions']}")
        print()
        
        # Execute simple code
        print("Executing simple Python code...")
        code = """
print("Hello from sandbox!")
for i in range(5):
    print(f"Count: {i}")
"""
        
        async for result in client.execute_code(code, session_id="example-session"):
            if "text" in result:
                print(f"Output: {result['text'].strip()}")
            elif "error" in result:
                print(f"Error: {result['error']}")
            elif "image" in result:
                print(f"Image output (base64): {result['image'][:50]}...")
        
        print()
        
        # Execute code with matplotlib
        print("Executing code with matplotlib...")
        plot_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', linewidth=2, label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine Wave')
plt.legend()
plt.grid(True)
plt.show()

print("Plot generated!")
"""
        
        async for result in client.execute_code(plot_code, session_id="example-session"):
            if "text" in result:
                print(f"Output: {result['text'].strip()}")
            elif "error" in result:
                print(f"Error: {result['error']}")
            elif "image" in result:
                print(f"Generated plot (base64 length: {len(result['image'])} chars)")
        
        print()
        
        # List sessions
        print("Listing active sessions...")
        sessions = await client.list_sessions()
        print(f"Total sessions: {sessions['total']}")
        for session_id, info in sessions['sessions'].items():
            print(f"  {session_id}: {info['execution_count']} executions")
        
        print()
        
        # Execute code with error
        print("Executing code with intentional error...")
        error_code = """
print("This will work")
undefined_variable  # This will cause an error
print("This won't be reached")
"""
        
        async for result in client.execute_code(error_code):
            if "text" in result:
                print(f"Output: {result['text'].strip()}")
            elif "error" in result:
                print(f"Error caught: {result['error'][:100]}...")


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import aiohttp
    except ImportError:
        print("Please install aiohttp: pip install aiohttp")
        exit(1)
    
    asyncio.run(main())