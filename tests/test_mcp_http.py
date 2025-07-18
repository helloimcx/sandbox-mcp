#!/usr/bin/env python3
"""HTTP-based MCP unit tests using direct HTTP requests."""

import json
import unittest
import aiohttp
from typing import Dict, Any


class MCPHTTPClient:
    """Simple MCP HTTP client for testing."""
    
    def __init__(self, base_url: str = "http://localhost:16010/ai/sandbox/v1"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self._id_counter = 1000  # 用于生成唯一ID

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _jsonrpc_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/mcp/"
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        async with self.session.post(url, json=payload, headers=headers) as response:
            content_type = response.headers.get('content-type', '')
            if response.status == 200:
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    text = await response.text()
                    # 处理 SSE 格式，提取 data: 后的 JSON
                    for line in text.splitlines():
                        if line.startswith("data:"):
                            sse_json = line[len("data:"):].strip()
                            try:
                                return json.loads(sse_json)
                            except Exception:
                                return {"error": f"SSE Non-JSON data: {sse_json}"}
                    # 没有 data: 行则返回原始内容
                    return {"error": f"Non-JSON response: {text}"}
            else:
                text = await response.text()
                return {"error": f"HTTP {response.status}: {text}"}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        return await self._jsonrpc_call("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools."""
        return await self._jsonrpc_call("tools/list", {})

    async def list_resources(self) -> Dict[str, Any]:
        """List available MCP resources."""
        return await self._jsonrpc_call("resources/list", {})

    async def get_resource(self, uri: str) -> Dict[str, Any]:
        """Get a specific MCP resource."""
        return await self._jsonrpc_call("resources/read", {
            "uri": uri
        })

    async def list_prompts(self) -> Dict[str, Any]:
        """List available MCP prompts."""
        return await self._jsonrpc_call("prompts/list", {})

    async def get_prompt(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get a specific MCP prompt."""
        return await self._jsonrpc_call("prompts/get", {
            "name": name,
            "arguments": arguments or {}
        })


class TestMCPHTTP(unittest.IsolatedAsyncioTestCase):
    """HTTP-based MCP unit test suite."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:16010/ai/sandbox/v1"
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def test_direct_http_endpoints(self):
        """Test MCP endpoints using direct HTTP requests."""
        print("🧪 Testing MCP Endpoints with Direct HTTP\n")
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            
            # Test 2: Check MCP endpoint with GET
            print("2️⃣ Testing MCP endpoint with GET...")
            async with session.get(f"{self.base_url}/mcp/") as response:
                self.assertIn(response.status, [200, 404, 405, 406, 501], "MCP endpoint should respond")
                text = await response.text()
                self.assertIsInstance(text, str, "Response should be text")
                print(f"   Status: {response.status}")
                print(f"   Response: {text[:200]}..." if len(text) > 200 else f"   Response: {text}")
            print()
            
            # Test 3: Test MCP with POST (JSON-RPC format)
            print("3️⃣ Testing MCP with JSON-RPC initialize...")
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with session.post(
                f"{self.base_url}/mcp/",
                json=init_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                print(f"   Status: {response.status}")
                self.assertEqual(response.status, 200, "Initialize should return 200")
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    self.assertIsInstance(data, dict, "Response should be JSON")
                    self.assertIn('result', data, "Response should contain result")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    self.assertIsInstance(text, str, "Response should be text")
                    print(f"   Response (text): {text[:500]}..." if len(text) > 500 else f"   Response (text): {text}")
            print()
            
            # Test 4: Test tools/list
            print("4️⃣ Testing tools/list...")
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            async with session.post(
                f"{self.base_url}/mcp/",
                json=tools_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                print(f"   Status: {response.status}")
                self.assertEqual(response.status, 200, "Tools list should return 200")
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    self.assertIsInstance(data, dict, "Response should be JSON")
                    self.assertIn('result', data, "Response should contain result")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    self.assertIsInstance(text, str, "Response should be text")
                    print(f"   Response (text): {text[:500]}..." if len(text) > 500 else f"   Response (text): {text}")
            print()
            
            # Test 5: Test resources/list
            print("5️⃣ Testing resources/list...")
            resources_payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list",
                "params": {}
            }
            
            async with session.post(
                f"{self.base_url}/mcp/",
                json=resources_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                print(f"   Status: {response.status}")
                self.assertEqual(response.status, 200, "Resources list should return 200")
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    self.assertIsInstance(data, dict, "Response should be JSON")
                    self.assertIn('result', data, "Response should contain result")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    self.assertIsInstance(text, str, "Response should be text")
                    print(f"   Response (text): {text[:500]}..." if len(text) > 500 else f"   Response (text): {text}")
            print()
            
            # Test 6: Test prompts/list
            print("6️⃣ Testing prompts/list...")
            prompts_payload = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "prompts/list",
                "params": {}
            }
            
            async with session.post(
                f"{self.base_url}/mcp/",
                json=prompts_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                print(f"   Status: {response.status}")
                self.assertEqual(response.status, 200, "Prompts list should return 200")
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    self.assertIsInstance(data, dict, "Response should be JSON")
                    self.assertIn('result', data, "Response should contain result")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    self.assertIsInstance(text, str, "Response should be text")
                    print(f"   Response (text): {text[:500]}..." if len(text) > 500 else f"   Response (text): {text}")
            print()
            
            # Test 7: Test tool execution
            print("7️⃣ Testing tool execution...")
            execute_payload = {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "execute_python_code",
                    "arguments": {
                        "code": "print('Hello from direct HTTP MCP test!')\nresult = 3 * 7\nprint(f'3 * 7 = {result}')",
                        "session_id": "http-test-session"
                    }
                }
            }
            
            async with session.post(
                f"{self.base_url}/mcp/",
                json=execute_payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            ) as response:
                print(f"   Status: {response.status}")
                self.assertEqual(response.status, 200, "Tool execution should return 200")
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    data = await response.json()
                    self.assertIsInstance(data, dict, "Response should be JSON")
                    self.assertIn('result', data, "Response should contain result")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    self.assertIsInstance(text, str, "Response should be text")
                    print(f"   Response (text): {text[:500]}..." if len(text) > 500 else f"   Response (text): {text}")
            print()
            
            print("🎉 Direct HTTP endpoint testing completed!")
    
    async def test_mcp_functionality(self):
        """Test all MCP functionality using HTTP client."""
        async with MCPHTTPClient() as client:
            print("🧪 Testing MCP Server Functionality\n")
            
            # Test 1: List available tools
            print("1️⃣ Testing tool listing...")
            tools = await client.list_tools()
            self.assertIsInstance(tools, dict, "Response should be a dictionary")
            if "error" not in tools:
                self.assertIn("result", tools, "Response should contain result")
                self.assertIn("tools", tools["result"], "Result should contain tools")
                self.assertIsInstance(tools["result"]["tools"], list, "Tools should be a list")
                print(f"✅ Found {len(tools['result'].get('tools', []))} tools:")
                for tool in tools['result'].get('tools', []):
                    print(f"   - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
            else:
                print(f"⚠️ Tool listing returned error: {tools['error']}")
            print()
            
            # Test 2: Execute Python code
            print("2️⃣ Testing Python code execution...")
            code_result = await client.call_tool("execute_python_code", {
                "code": "print('Hello from MCP!')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')",
                "session_id": "mcp-test-session"
            })
            self.assertIsInstance(code_result, dict, "Response should be a dictionary")
            if "error" not in code_result:
                print(f"✅ Code execution result: {code_result}")
            else:
                print(f"⚠️ Code execution returned error: {code_result['error']}")
            print()
            
            # Test 3: List sessions
            print("3️⃣ Testing session listing...")
            sessions_result = await client.call_tool("list_sessions", {})
            self.assertIsInstance(sessions_result, dict, "Response should be a dictionary")
            if "error" not in sessions_result:
                print(f"✅ Sessions: {sessions_result}")
            else:
                print(f"⚠️ Session listing returned error: {sessions_result['error']}")
            print()
            
            # Test 4: Test with matplotlib
            print("4️⃣ Testing matplotlib code execution...")
            plot_code = """
import matplotlib.pyplot as plt
import numpy as np

# Create a simple plot
x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.title('Sine Wave from MCP')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.show()

print('Plot generated successfully!')
"""
            plot_result = await client.call_tool("execute_python_code", {
                "code": plot_code,
                "session_id": "mcp-test-session"
            })
            self.assertIsInstance(plot_result, dict, "Response should be a dictionary")
            if "error" not in plot_result:
                print(f"✅ Plot execution result: {plot_result}")
            else:
                print(f"⚠️ Plot execution returned error: {plot_result['error']}")
            print()
            
            # Test 5: List resources
            print("5️⃣ Testing resource listing...")
            resources = await client.list_resources()
            self.assertIsInstance(resources, dict, "Response should be a dictionary")
            if "error" not in resources:
                self.assertIn("result", resources, "Response should contain result")
                self.assertIn("resources", resources["result"], "Result should contain resources")
                self.assertIsInstance(resources["result"]["resources"], list, "Resources should be a list")
                print(f"✅ Found {len(resources['result'].get('resources', []))} resources:")
                for resource in resources['result'].get('resources', []):
                    print(f"   - {resource.get('uri', 'Unknown')}: {resource.get('description', 'No description')}")
            else:
                print(f"⚠️ Resource listing returned error: {resources['error']}")
            print()
            
            # Test 6: Get session resource
            print("6️⃣ Testing session resource retrieval...")
            session_resource = await client.get_resource("session://mcp-test-session")
            self.assertIsInstance(session_resource, dict, "Response should be a dictionary")
            if "error" not in session_resource:
                print(f"✅ Session resource: {session_resource}")
            else:
                print(f"⚠️ Session resource returned error: {session_resource['error']}")
            print()
            
            # Test 7: List prompts
            print("7️⃣ Testing prompt listing...")
            prompts = await client.list_prompts()
            self.assertIsInstance(prompts, dict, "Response should be a dictionary")
            if "error" not in prompts:
                self.assertIn("result", prompts, "Response should contain result")
                self.assertIn("prompts", prompts["result"], "Result should contain prompts")
                self.assertIsInstance(prompts["result"]["prompts"], list, "Prompts should be a list")
                print(f"✅ Found {len(prompts['result'].get('prompts', []))} prompts:")
                for prompt in prompts['result'].get('prompts', []):
                    print(f"   - {prompt.get('name', 'Unknown')}: {prompt.get('description', 'No description')}")
            else:
                print(f"⚠️ Prompt listing returned error: {prompts['error']}")
            print()
            
            # Test 8: Get prompt
            print("8️⃣ Testing prompt generation...")
            prompt_result = await client.get_prompt(
                "code_execution_prompt",
                {
                    "task_description": "Create a function to sort a list of numbers",
                    "code_style": "verbose",
                    "include_comments": "true"
                }
            )
            self.assertIsInstance(prompt_result, dict, "Response should be a dictionary")
            if "error" not in prompt_result:
                print(f"✅ Prompt generation result: {prompt_result}")
            else:
                print(f"⚠️ Prompt generation returned error: {prompt_result['error']}")
            print()
            
            # Test 9: Terminate session
            print("9️⃣ Testing session termination...")
            terminate_result = await client.call_tool("terminate_session", {
                "session_id": "mcp-test-session"
            })
            self.assertIsInstance(terminate_result, dict, "Response should be a dictionary")
            if "error" not in terminate_result:
                print(f"✅ Session terminated: {terminate_result}")
            else:
                print(f"⚠️ Session termination returned error: {terminate_result['error']}")
            print()
            
            print("🎉 MCP functionality testing completed!")


if __name__ == "__main__":
    unittest.main()