"""端到端测试 - 完整工作流程"""

import pytest
import requests
import time
import json
from typing import Dict, Any

# 测试配置
BASE_URL = "http://localhost:16010/ai/sandbox/v1/api"
HEADERS = {
    "Content-Type": "application/json"
}


class TestFullWorkflow:
    """完整工作流程端到端测试"""
    
    def make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> requests.Response:
        """发送HTTP请求的辅助方法"""
        url = f"{BASE_URL}{endpoint}"
        proxies = {"http": None, "https": None}
        
        if method.upper() == "GET":
            return requests.get(url, headers=HEADERS, proxies=proxies)
        elif method.upper() == "POST":
            return requests.post(url, headers=HEADERS, json=data, proxies=proxies)
        elif method.upper() == "DELETE":
            return requests.delete(url, headers=HEADERS, proxies=proxies)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def test_complete_session_lifecycle_with_file_operations(self):
        """测试完整的会话生命周期和文件操作"""
        session_id = None
        
        try:
            # 1. 创建会话并下载文件
            print("\n=== 步骤1: 创建会话并下载文件 ===")
            create_response = self.make_request("POST", "/sessions", {
                "session_id": "e2e_test_session",
                "files": []
            })
            
            assert create_response.status_code == 200
            create_data = create_response.json()
            assert create_data["resultCode"] == 0
            
            session_id = create_data["data"]["session_id"]
            working_dir = create_data["data"]["working_directory"]
            
            print(f"✅ 会话创建成功: {session_id}")
            print(f"✅ 工作目录: {working_dir}")
            
            # 2. 执行Python代码 - 创建文件
            print("\n=== 步骤2: 执行代码创建文件 ===")
            code_create_file = """
import os
import json

# 创建测试文件
with open('test_data.json', 'w') as f:
    json.dump({'message': 'Hello from E2E test', 'timestamp': '2024-01-01'}, f)

# 创建Python脚本
with open('calculator.py', 'w') as f:
    f.write('''
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    print(f"5 + 3 = {add(5, 3)}")
    print(f"4 * 6 = {multiply(4, 6)}")
''')

print(f"当前工作目录: {os.getcwd()}")
print(f"目录内容: {os.listdir('.')}")
"""
            
            exec_response = self.make_request("POST", "/execute_sync", {
                "code": code_create_file,
                "session_id": session_id
            })
            
            assert exec_response.status_code == 200
            exec_data = exec_response.json()
            assert exec_data["resultCode"] == 0
            assert len(exec_data["data"]["texts"]) > 0
            
            print("✅ 文件创建成功")
            for text in exec_data["data"]["texts"]:
                print(f"   {text}")
            
            # 3. 执行Python代码 - 读取和处理文件
            print("\n=== 步骤3: 读取和处理文件 ===")
            code_process_file = """
import json
import subprocess
import sys

# 读取JSON文件
with open('test_data.json', 'r') as f:
    data = json.load(f)
    print(f"读取到的数据: {data}")

# 执行Python脚本
result = subprocess.run([sys.executable, 'calculator.py'], 
                       capture_output=True, text=True)
print("计算器脚本输出:")
print(result.stdout)

# 创建结果文件
results = {
    'original_data': data,
    'calculations': result.stdout.strip().split('\n'),
    'status': 'completed'
}

with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("处理完成，结果已保存到 results.json")
"""
            
            exec_response2 = self.make_request("POST", "/execute_sync", {
                "code": code_process_file,
                "session_id": session_id
            })
            
            assert exec_response2.status_code == 200
            exec_data2 = exec_response2.json()
            assert exec_data2["resultCode"] == 0
            
            print("✅ 文件处理成功")
            for text in exec_data2["data"]["texts"]:
                print(f"   {text}")
            
            # 4. 验证文件内容
            print("\n=== 步骤4: 验证文件内容 ===")
            code_verify = """
import os
import json

# 检查所有文件是否存在
expected_files = ['test_data.json', 'calculator.py', 'results.json']
for filename in expected_files:
    if os.path.exists(filename):
        print(f"✅ {filename} 存在")
        if filename.endswith('.json'):
            with open(filename, 'r') as f:
                content = json.load(f)
                print(f"   内容: {content}")
    else:
        print(f"❌ {filename} 不存在")

# 显示最终目录状态
print(f"\n最终目录内容: {os.listdir('.')}")
"""
            
            exec_response3 = self.make_request("POST", "/execute_sync", {
                "code": code_verify,
                "session_id": session_id
            })
            
            assert exec_response3.status_code == 200
            exec_data3 = exec_response3.json()
            assert exec_data3["resultCode"] == 0
            
            print("✅ 文件验证完成")
            for text in exec_data3["data"]["texts"]:
                print(f"   {text}")
            
            # 5. 测试错误处理
            print("\n=== 步骤5: 测试错误处理 ===")
            code_with_error = """
# 故意引发错误
try:
    result = 1 / 0
except ZeroDivisionError as e:
    print(f"捕获到预期错误: {e}")
    print("错误处理正常")

# 尝试访问不存在的文件
try:
    with open('nonexistent.txt', 'r') as f:
        content = f.read()
except FileNotFoundError as e:
    print(f"捕获到文件不存在错误: {e}")
    print("文件错误处理正常")
"""
            
            exec_response4 = self.make_request("POST", "/execute_sync", {
                "code": code_with_error,
                "session_id": session_id
            })
            
            assert exec_response4.status_code == 200
            exec_data4 = exec_response4.json()
            assert exec_data4["resultCode"] == 0
            
            print("✅ 错误处理测试完成")
            for text in exec_data4["data"]["texts"]:
                print(f"   {text}")
            
            # 6. 测试会话状态查询
            print("\n=== 步骤6: 查询会话状态 ===")
            status_response = self.make_request("GET", f"/sessions/{session_id}")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"✅ 会话状态查询成功: {status_data}")
            else:
                print(f"⚠️  会话状态查询失败: {status_response.status_code}")
            
        finally:
            # 7. 清理 - 删除会话
            if session_id:
                print(f"\n=== 步骤7: 清理会话 {session_id} ===")
                delete_response = self.make_request("DELETE", f"/sessions/{session_id}")
                
                if delete_response.status_code == 200:
                    print("✅ 会话删除成功")
                else:
                    print(f"⚠️  会话删除失败: {delete_response.status_code}")
    
    def test_session_pool_reuse_workflow(self):
        """测试会话池复用工作流程"""
        session_ids = []
        
        try:
            print("\n=== 会话池复用测试 ===")
            
            # 创建多个会话
            for i in range(3):
                print(f"\n--- 创建会话 {i+1} ---")
                response = self.make_request("POST", "/sessions", {
                    "session_id": f"pool_test_{i+1}",
                    "files": []
                })
                
                assert response.status_code == 200
                data = response.json()
                session_id = data["data"]["session_id"]
                session_ids.append(session_id)
                
                # 在每个会话中执行简单代码
                exec_response = self.make_request("POST", "/execute_sync", {
                    "code": f"print(f'Hello from session {i+1}: {{__file__ if '__file__' in globals() else \"interactive\"}}')",
                    "session_id": session_id
                })
                
                assert exec_response.status_code == 200
                print(f"✅ 会话 {session_id} 创建并执行成功")
            
            # 删除前两个会话（应该返回到池中）
            for i in range(2):
                print(f"\n--- 删除会话 {session_ids[i]} ---")
                delete_response = self.make_request("DELETE", f"/sessions/{session_ids[i]}")
                assert delete_response.status_code == 200
                print(f"✅ 会话 {session_ids[i]} 已删除（返回池中）")
            
            # 等待一下让会话返回池中
            time.sleep(2)
            
            # 创建新会话（应该从池中复用）
            print("\n--- 创建新会话（应该复用池中会话） ---")
            response = self.make_request("POST", "/sessions", {
                "session_id": "reused_session",
                "files": []
            })
            
            assert response.status_code == 200
            data = response.json()
            new_session_id = data["data"]["session_id"]
            session_ids.append(new_session_id)
            
            # 验证新会话工作正常
            exec_response = self.make_request("POST", "/execute_sync", {
                "code": "import os; print(f'Reused session working directory: {os.getcwd()}')",
                "session_id": new_session_id
            })
            
            assert exec_response.status_code == 200
            exec_data = exec_response.json()
            assert len(exec_data["data"]["texts"]) > 0
            
            print(f"✅ 复用会话 {new_session_id} 工作正常")
            for text in exec_data["data"]["texts"]:
                print(f"   {text}")
            
        finally:
            # 清理所有会话
            print("\n=== 清理所有测试会话 ===")
            for session_id in session_ids:
                try:
                    delete_response = self.make_request("DELETE", f"/sessions/{session_id}")
                    if delete_response.status_code == 200:
                        print(f"✅ 会话 {session_id} 清理成功")
                    else:
                        print(f"⚠️  会话 {session_id} 清理失败")
                except Exception as e:
                    print(f"⚠️  清理会话 {session_id} 时出错: {e}")
    
    def test_concurrent_sessions_workflow(self):
        """测试并发会话工作流程"""
        import threading
        import queue
        
        results = queue.Queue()
        session_ids = []
        
        def create_and_test_session(session_name: str):
            """创建并测试会话的线程函数"""
            try:
                # 创建会话
                response = self.make_request("POST", "/sessions", {
                    "session_id": f"concurrent_{session_name}",
                    "files": []
                })
                
                if response.status_code != 200:
                    results.put((session_name, False, f"创建失败: {response.status_code}"))
                    return
                
                data = response.json()
                session_id = data["data"]["session_id"]
                session_ids.append(session_id)
                
                # 执行计算任务
                code = f"""
import time
import random

# 模拟一些计算工作
result = 0
for i in range(100):
    result += i * random.random()
    if i % 20 == 0:
        time.sleep(0.01)  # 短暂休眠

print(f"Session {session_name}: 计算完成，结果 = {{result:.2f}}")
print(f"Session {session_name}: 工作目录 = {{__import__('os').getcwd()}}")
"""
                
                exec_response = self.make_request("POST", "/execute_sync", {
                    "code": code,
                    "session_id": session_id
                })
                
                if exec_response.status_code == 200:
                    exec_data = exec_response.json()
                    if exec_data["resultCode"] == 0 and exec_data["data"]["texts"]:
                        results.put((session_name, True, exec_data["data"]["texts"]))
                    else:
                        results.put((session_name, False, "执行无输出"))
                else:
                    results.put((session_name, False, f"执行失败: {exec_response.status_code}"))
                    
            except Exception as e:
                results.put((session_name, False, f"异常: {str(e)}"))
        
        try:
            print("\n=== 并发会话测试 ===")
            
            # 创建多个线程并发测试
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_and_test_session, args=(f"thread_{i+1}",))
                threads.append(thread)
                thread.start()
            
            # 等待所有线程完成
            for thread in threads:
                thread.join(timeout=30)
            
            # 收集结果
            success_count = 0
            while not results.empty():
                session_name, success, output = results.get()
                if success:
                    success_count += 1
                    print(f"✅ {session_name} 成功:")
                    if isinstance(output, list):
                        for line in output:
                            print(f"   {line}")
                    else:
                        print(f"   {output}")
                else:
                    print(f"❌ {session_name} 失败: {output}")
            
            print(f"\n并发测试结果: {success_count}/5 个会话成功")
            assert success_count >= 3, f"并发测试失败，只有 {success_count} 个会话成功"
            
        finally:
            # 清理会话
            print("\n=== 清理并发测试会话 ===")
            for session_id in session_ids:
                try:
                    delete_response = self.make_request("DELETE", f"/sessions/{session_id}")
                    if delete_response.status_code == 200:
                        print(f"✅ 会话 {session_id} 清理成功")
                except Exception as e:
                    print(f"⚠️  清理会话 {session_id} 时出错: {e}")
    
    @pytest.mark.skipif(
        True,  # 默认跳过，因为需要外部网络
        reason="需要外部网络连接，在CI环境中可能不稳定"
    )
    def test_file_download_workflow(self):
        """测试文件下载工作流程（需要网络连接）"""
        session_id = None
        
        try:
            print("\n=== 文件下载工作流程测试 ===")
            
            # 创建会话并下载文件
            response = self.make_request("POST", "/sessions", {
                "session_id": "download_test",
                "file_urls": [
                    "https://raw.githubusercontent.com/python/cpython/main/README.rst"
                ]
            })
            
            assert response.status_code == 200
            data = response.json()
            session_id = data["data"]["session_id"]
            
            print(f"✅ 会话创建成功: {session_id}")
            print(f"下载的文件: {data['data']['downloaded_files']}")
            if data['data']['errors']:
                print(f"下载错误: {data['data']['errors']}")
            
            # 验证文件是否可以读取
            code = """
import os

# 列出目录内容
files = os.listdir('.')
print(f"目录内容: {files}")

# 尝试读取README文件
for filename in files:
    if 'README' in filename.upper():
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()[:200]  # 只读前200字符
                print(f"成功读取 {filename}:")
                print(content + "...")
                break
        except Exception as e:
            print(f"读取 {filename} 失败: {e}")
else:
    print("未找到README文件")
"""
            
            exec_response = self.make_request("POST", "/execute_sync", {
                "code": code,
                "session_id": session_id
            })
            
            assert exec_response.status_code == 200
            exec_data = exec_response.json()
            
            print("✅ 文件读取测试完成")
            for text in exec_data["data"]["texts"]:
                print(f"   {text}")
                
        finally:
            if session_id:
                delete_response = self.make_request("DELETE", f"/sessions/{session_id}")
                print(f"✅ 测试会话已清理")


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    test = TestFullWorkflow()
    try:
        test.test_complete_session_lifecycle_with_file_operations()
        print("\n🎉 完整工作流程测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        raise