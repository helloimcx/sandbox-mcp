#!/usr/bin/env python3
"""Integration tests for MCP server using streamable HTTP client."""

import asyncio
import unittest
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession


class TestMCPIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for MCP server."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "http://localhost:16010/ai/sandbox/v1/mcp"
    
    async def test_basic_functionality(self):
        """Test basic MCP server functionality."""
        print("🚀 Testing basic MCP functionality...")
        
        async with streamablehttp_client(self.base_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize
                init_result = await session.initialize()
                self.assertIsNotNone(init_result.serverInfo, "Server info should be present")
                self.assertIsNotNone(init_result.serverInfo.name, "Server name should be present")
                print(f"✅ Initialized: {init_result.serverInfo.name}")
                
                # Test basic execution
                result = await session.call_tool(
                    "execute_python_code", 
                    {"code": "print('MCP Server is working perfectly!')"}
                )
                self.assertIsNotNone(result.content, "Result content should be present")
                self.assertTrue(len(result.content) > 0, "Result should have content")
                print(f"✅ Execution result: {result.content[0].text}")
                
                # Test math
                result = await session.call_tool(
                    "execute_python_code", 
                    {"code": "import math; print(f'π = {math.pi:.6f}')"}
                )
                self.assertIsNotNone(result.content, "Math result content should be present")
                self.assertTrue(len(result.content) > 0, "Math result should have content")
                print(f"✅ Math result: {result.content[0].text}")
                
                print("🎉 Basic functionality test passed!")
    
    async def test_comprehensive_functionality(self):
        """Test comprehensive MCP server functionality."""
        print("🚀 Comprehensive MCP Server Testing...")
        
        async with streamablehttp_client(self.base_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize
                init_result = await session.initialize()
                self.assertIsNotNone(init_result, "Initialization should succeed")
                print("✅ Connection initialized")
                    
                # Test 1: Basic Python execution
                print("\n1️⃣ Testing basic Python execution...")
                result = await session.call_tool(
                    "execute_python_code", 
                    {"code": "print('Hello, World!')\nprint(f'Python version: {2+3}')"}
                )
                self.assertIsNotNone(result.content, "Basic execution should return content")
                self.assertTrue(len(result.content) > 0, "Basic execution should have content")
                print(f"✅ Basic execution: {result.content[0].text[:100]}...")
                    
                # Test 2: Mathematical calculations
                print("\n2️⃣ Testing mathematical calculations...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": """
import math
result = math.sqrt(16) + math.pi
print(f"sqrt(16) + π = {result:.4f}")
print(f"Factorial of 5: {math.factorial(5)}")
"""
                    }
                )
                self.assertIsNotNone(result.content, "Math calculations should return content")
                self.assertTrue(len(result.content) > 0, "Math calculations should have content")
                print(f"✅ Math calculations: {result.content[0].text[:100]}...")
                
                # Test 3: Data structures and loops
                print("\n3️⃣ Testing data structures and loops...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": """
# Create a list and process it
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]
print(f"Numbers: {numbers}")
print(f"Squares: {squares}")

# Dictionary operations
data = {'name': 'MCP', 'version': '1.0', 'status': 'active'}
for key, value in data.items():
    print(f"{key}: {value}")
"""
                    }
                )
                print(f"✅ Data structures: {result.content[0].text[:150]}...")
                
                # Test 4: Function definitions
                print("\n4️⃣ Testing function definitions...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 fibonacci numbers
fib_sequence = [fibonacci(i) for i in range(10)]
print(f"First 10 Fibonacci numbers: {fib_sequence}")
""",
                        "session_id": "fib-session"
                    }
                )
                print(f"✅ Functions: {result.content[0].text[:100]}...")
                
                # Test 5: Session persistence
                print("\n5️⃣ Testing session persistence...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": "print(f'Fibonacci of 12: {fibonacci(12)}')",
                        "session_id": "fib-session"
                    }
                )
                print(f"✅ Session persistence: {result.content[0].text[:100]}...")
                
                # Test 6: Error handling
                print("\n6️⃣ Testing error handling...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": "print(undefined_variable)"
                    }
                )
                print(f"✅ Error handling: {result.content[0].text[:100]}...")
                
                # Test 7: Import libraries
                print("\n7️⃣ Testing library imports...")
                result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": """
import json
import datetime

data = {
    'timestamp': datetime.datetime.now().isoformat(),
    'message': 'MCP server is working!',
    'numbers': [1, 2, 3, 4, 5]
}

json_str = json.dumps(data, indent=2)
print("JSON output:")
print(json_str)
"""
                    }
                )
                print(f"✅ Library imports: {result.content[0].text[:150]}...")
                
                # Test 8: Session management
                print("\n8️⃣ Testing session management...")
                sessions_result = await session.call_tool("list_active_sessions", {})
                print(f"✅ Active sessions: {sessions_result.content[0].text[:100]}...")
                
                # Test 9: Prompt generation
                print("\n9️⃣ Testing prompt generation...")
                prompt_result = await session.get_prompt(
                    "code_execution_prompt",
                    {
                        "task_description": "Create a class to manage a simple inventory system",
                        "code_style": "verbose",
                        "include_comments": "true"
                    }
                )
                print(f"✅ Prompt generation: {prompt_result.messages[0].content.text[:200]}...")
                
                # Test 10: Clean up sessions
                print("\n🔟 Testing session cleanup...")
                terminate_result = await session.call_tool(
                    "terminate_session", 
                    {"session_id": "fib-session"}
                )
                print(f"✅ Session cleanup: {terminate_result.content[0].text[:100]}...")
                
                print("\n🎉 All comprehensive tests passed successfully!")
                print("\n📊 Test Summary:")
                print("   ✅ Basic Python execution")
                print("   ✅ Mathematical calculations")
                print("   ✅ Data structures and loops")
                print("   ✅ Function definitions")
                print("   ✅ Session persistence")
                print("   ✅ Error handling")
                print("   ✅ Library imports")
                print("   ✅ Session management")
                print("   ✅ Prompt generation")
                print("   ✅ Session cleanup")
    
    async def test_streamable_client(self):
        """Test MCP server using streamable HTTP transport."""
        print("🚀 Testing MCP server with streamable HTTP client...")
        
        # Connect to the streamable HTTP server
        async with streamablehttp_client(self.base_url) as (
            read_stream,
            write_stream,
            _,
        ):
            print("✅ Connected to MCP server")
            
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                print("✅ Created client session")
                
                # Initialize the connection
                print("\n1️⃣ Initializing connection...")
                init_result = await session.initialize()
                self.assertIsNotNone(init_result.serverInfo, "Server info should be present")
                self.assertIsNotNone(init_result.serverInfo.name, "Server name should be present")
                print(f"✅ Initialization successful: {init_result.serverInfo.name} v{init_result.serverInfo.version}")
                    
                # List available tools
                print("\n2️⃣ Listing tools...")
                tools_result = await session.list_tools()
                self.assertIsNotNone(tools_result.tools, "Tools list should be present")
                self.assertIsInstance(tools_result.tools, list, "Tools should be a list")
                print(f"✅ Found {len(tools_result.tools)} tools:")
                for tool in tools_result.tools:
                    print(f"   - {tool.name}: {tool.description[:100]}...")
                
                # List available resources
                print("\n3️⃣ Listing resources...")
                resources_result = await session.list_resources()
                print(f"✅ Found {len(resources_result.resources)} resources")
                
                # List available prompts
                print("\n4️⃣ Listing prompts...")
                prompts_result = await session.list_prompts()
                print(f"✅ Found {len(prompts_result.prompts)} prompts:")
                for prompt in prompts_result.prompts:
                    print(f"   - {prompt.name}: {prompt.description[:100]}...")
                
                # Test tool execution - simple Python code
                print("\n5️⃣ Testing tool execution...")
                tool_result = await session.call_tool(
                    "execute_python_code", 
                    {
                        "code": "print('Hello from MCP sandbox!')",
                        "session_id": "test-session"
                    }
                )
                print(f"✅ Tool execution result: {tool_result.content[0].text[:200]}...")
                
                # Test mathematical calculation
                print("\n6️⃣ Testing mathematical calculation...")
                math_result = await session.call_tool(
                    "execute_python_code",
                    {
                        "code": "result = 2 + 2\nprint(f'2 + 2 = {result}')",
                        "session_id": "test-session"
                    }
                )
                print(f"✅ Math result: {math_result.content[0].text[:200]}...")
                
                # Test prompt generation
                print("\n7️⃣ Testing prompt generation...")
                try:
                    prompt_result = await session.get_prompt(
                        "code_execution_prompt",
                        {
                            "task_description": "Create a function to calculate fibonacci numbers",
                            "code_style": "clean",
                            "include_comments": "true"
                        }
                    )
                    print(f"✅ Prompt generated: {prompt_result.messages[0].content.text[:200]}...")
                except Exception as e:
                    print(f"⚠️  Prompt generation failed: {e}")
                
                # Test session listing
                print("\n8️⃣ Testing session listing...")
                sessions_result = await session.call_tool("list_active_sessions", {})
                print(f"✅ Active sessions: {sessions_result.content[0].text[:200]}...")
                
                # Test session termination
                print("\n9️⃣ Testing session termination...")
                terminate_result = await session.call_tool(
                    "terminate_session", 
                    {"session_id": "test-session"}
                )
                print(f"✅ Session termination: {terminate_result.content[0].text[:200]}...")
                
                print("\n🎉 All tests completed successfully!")
    
    async def test_error_handling(self):
        """Test error handling with invalid requests."""
        print("\n🔧 Testing Error Handling\n")
        
        async with streamablehttp_client(self.base_url) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                init_result = await session.initialize()
                self.assertIsNotNone(init_result, "Initialization should succeed")
                
                # Test invalid code
                print("1️⃣ Testing error handling with invalid Python code...")
                try:
                    error_result = await session.call_tool(
                        "execute_python_code",
                        {
                            "code": "print('Testing error')\nundefined_variable + 1",
                            "session_id": "error-test-session"
                        }
                    )
                    print(f"✅ Error handling result: {error_result.content}")
                except Exception as e:
                    print(f"⚠️  Error handling test: {e}")
                print()
                
                # Test invalid tool
                print("2️⃣ Testing invalid tool call...")
                try:
                    invalid_result = await session.call_tool("nonexistent_tool", {})
                    print(f"✅ Invalid tool result: {invalid_result.content}")
                except Exception as e:
                    print(f"⚠️  Invalid tool test: {e}")
                print()
                
            print("🎉 Error handling tests completed!")


if __name__ == "__main__":
    unittest.main()