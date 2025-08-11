import requests
import time

BASE_URL = "http://localhost:16010/ai/sandbox/v1/api"

def test_health_check():
    resp = requests.get("http://localhost:16010/health", proxies={"http": None, "https": None})
    assert resp.status_code == 200

def test_execute_code():
    payload = {"code": "print(1+1)"}
    resp = requests.post(f"{BASE_URL}/execute_sync", json=payload, proxies={"http": None, "https": None})
    assert resp.status_code == 200
    # 可选：检查返回内容格式
    lines = resp.text.strip().split("\n")
    print(lines)
    assert len(lines) > 0
    
def test_list_sessions():
    resp = requests.get(f"{BASE_URL}/sessions", proxies={"http": None, "https": None})
    assert resp.status_code == 200
    data = resp.json()
    print("List sessions response:")
    print(data)
    print("Sessions data structure:")
    if "sessions" in data:
        print(f"Type of sessions: {type(data['sessions'])}")
        if len(data["sessions"]) > 0:
            # sessions是一个字典，不能用索引访问
            print(f"Sessions keys: {list(data['sessions'].keys())}")
            first_key = next(iter(data['sessions']))
            print(f"First session: {data['sessions'][first_key]}")
    assert "sessions" in data
    assert "total" in data

def test_create_session_with_files():
    # 测试创建带有文件下载的会话
    payload = {
        "file_urls": ["https://raw.githubusercontent.com/python/cpython/main/README.rst"],
        "timeout": 30
    }
    resp = requests.post(f"{BASE_URL}/sessions", json=payload, proxies={"http": None, "https": None})
    assert resp.status_code == 200
    data = resp.json()
    print(data)
    
    # 验证响应结构
    assert "data" in data
    assert "session_id" in data["data"]
    assert "working_directory" in data["data"]
    assert "downloaded_files" in data["data"]
    assert "errors" in data["data"]
    
    # 验证文件已下载或有错误信息
    assert len(data["data"]["downloaded_files"]) > 0 or len(data["data"]["errors"]) > 0
    
    # 验证会话可用 - 执行简单代码
    session_id = data["data"]["session_id"]
    code = """
    import os
    print(os.getcwd())
    with open('README.rst', 'r') as f:
        content = f.read()
    print(content[:100])
    """
    exec_payload = {
        "code": code,
        "session_id": session_id
    }
    exec_resp = requests.post(f"{BASE_URL}/execute_sync", json=exec_payload, proxies={"http": None, "https": None})
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    print(exec_data)
    assert "data" in exec_data
    assert "texts" in exec_data["data"]
    assert len(exec_data["data"]["texts"]) > 0


def test_create_session_with_specific_id():
    # 测试创建带有指定session_id的会话
    session_id = f"test_session_{int(time.time())}"
    payload = {
        "session_id": session_id,
        "file_urls": ["https://www.example.com/"]
    }
    resp = requests.post(f"{BASE_URL}/sessions", json=payload, proxies={"http": None, "https": None})
    assert resp.status_code == 200
    data = resp.json()
    print(data)
    
    # 验证返回的session_id与请求中指定的相同
    assert "data" in data
    assert data["data"]["session_id"] == session_id
    assert "errors" in data["data"]
    
    # 验证文件已下载或有错误信息
    assert len(data["data"]["downloaded_files"]) > 0 or len(data["data"]["errors"]) > 0
    
    # 通过list_sessions API验证会话存在
    list_resp = requests.get(f"{BASE_URL}/sessions", proxies={"http": None, "https": None})
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    print(list_data)
    
    # 检查会话列表中是否包含我们创建的会话
    assert "sessions" in list_data
    assert session_id in list_data["sessions"]
