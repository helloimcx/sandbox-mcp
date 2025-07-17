import requests

BASE_URL = "http://localhost:16010/ai/sandbox/v1/api"

def test_health_check():
    resp = requests.get("http://localhost:16010/health", proxies={"http": None, "https": None})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "active_sessions" in data
    assert "uptime" in data

def test_execute_code():
    payload = {"code": "print(1+1)"}
    resp = requests.post(f"{BASE_URL}/execute", json=payload, proxies={"http": None, "https": None})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/x-ndjson")
    # 可选：检查返回内容格式
    lines = resp.text.strip().split("\n")
    print(lines)
    assert len(lines) > 0

def test_list_sessions():
    resp = requests.get(f"{BASE_URL}/sessions", proxies={"http": None, "https": None})
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert "total" in data
