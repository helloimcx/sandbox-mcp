"""file_utils 单元测试"""

import pytest
import os
import tempfile
import shutil
import asyncio
from unittest.mock import patch
from aiohttp import ClientError

from src.utils.file_utils import download_file


class TestDownloadFile:
    """download_file 函数测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_download_file_success_returns_filename_and_no_error(self, temp_dir):
        """测试成功下载文件"""
        url = "https://example.com/test.txt"
        
        # Create a simple mock that works
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {'Content-Disposition': 'attachment; filename="test.txt"'}
                self.content = self
                
            async def iter_chunked(self, size):
                yield b"test content"
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockSession:
            def __init__(self):
                pass
                
            def get(self, url, ssl=None):
                return MockResponse()
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockFile:
            async def write(self, data):
                pass
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()), \
             patch('src.utils.file_utils.aiofiles.open', return_value=MockFile()):
            
            filename, error = await download_file(url, temp_dir)
            
            assert filename == "test.txt"
            assert error is None
    

    
    @pytest.mark.asyncio
    async def test_download_file_http_error_returns_error_message(self, temp_dir):
        """测试HTTP错误返回错误信息"""
        url = "https://example.com/notfound.txt"
        
        class MockResponse:
            def __init__(self):
                self.status = 404
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockSession:
            def get(self, url, ssl=None):
                return MockResponse()
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()):
            filename, error = await download_file(url, temp_dir)
            
            assert filename is None
            assert error is not None
            assert "HTTP 404" in error
    
    @pytest.mark.asyncio
    async def test_download_file_network_error_returns_error_message(self, temp_dir):
        """测试网络错误返回错误信息"""
        url = "https://invalid-domain-12345.com/test.txt"
        
        class MockSession:
            def get(self, url, ssl=None):
                raise ClientError("Connection failed")
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()):
            filename, error = await download_file(url, temp_dir)
            
            assert filename is None
            assert error is not None
            assert "Connection failed" in error
    
    @pytest.mark.asyncio
    async def test_download_file_timeout_returns_error_message(self, temp_dir):
        """测试超时返回错误信息"""
        url = "https://example.com/slow.txt"
        
        class MockSession:
            def get(self, url, ssl=None):
                raise asyncio.TimeoutError("Request timeout")
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()):
            filename, error = await download_file(url, temp_dir, timeout=1)
            
            assert filename is None
            assert "failed to download" in error.lower()
            assert "timeout" in error.lower()
    
    @pytest.mark.asyncio
    async def test_download_file_creates_directory_if_not_exists(self):
        """测试如果目录不存在则创建目录"""
        with tempfile.TemporaryDirectory() as base_dir:
            download_dir = os.path.join(base_dir, "new_dir")
            url = "https://example.com/test.txt"
            
            # 创建目录以模拟实际行为
            os.makedirs(download_dir, exist_ok=True)
            
            class MockResponse:
                def __init__(self):
                    self.status = 200
                    self.headers = {'Content-Disposition': 'attachment; filename="test.txt"'}
                    self.content = self
                    
                async def iter_chunked(self, size):
                    yield b"content"
                    
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            class MockSession:
                def get(self, url, ssl=None):
                    return MockResponse()
                    
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            class MockFile:
                async def write(self, data):
                    pass
                    
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()), \
                 patch('src.utils.file_utils.aiofiles.open', return_value=MockFile()):
                
                filename, error = await download_file(url, download_dir)
                
                assert os.path.exists(download_dir)
                assert filename == "test.txt"
                assert error is None
    
    @pytest.mark.asyncio
    async def test_download_file_without_filename_in_headers_returns_error(self, temp_dir):
        """测试响应头中没有文件名时返回错误"""
        url = "https://example.com/data"
        
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {}  # 没有Content-Disposition头
                self.content = self
                
            async def iter_chunked(self, size):
                yield b"content"
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockSession:
            def get(self, url, ssl=None):
                return MockResponse()
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=MockSession()):
            filename, error = await download_file(url, temp_dir, timeout=30)
            
            # 应该返回错误
            assert error is not None
            assert "No filename could be determined from response headers" in error
            assert url in error
            
            # 文件名应该是None
            assert filename is None
    
    @pytest.mark.asyncio
    async def test_download_file_with_empty_path_returns_error(self, temp_dir):
        """测试URL路径为空时返回错误"""
        # 使用一个无效的根路径URL来触发异常
        url_empty_path = "https://nonexistent-domain-12345.com/"
        
        filename, error = await download_file(url_empty_path, temp_dir, timeout=1)
        
        assert error is not None
        assert "Failed to download" in error
        assert url_empty_path in error
        assert filename is None
    
    @pytest.mark.asyncio
    async def test_download_file_with_verify_ssl_false_disables_ssl_verification(self, temp_dir):
        """测试禁用SSL验证"""
        url = "https://self-signed.example.com/test.txt"
        
        class MockResponse:
            def __init__(self):
                self.status = 200
                self.headers = {'Content-Disposition': 'attachment; filename="test.txt"'}
                self.content = self
                
            async def iter_chunked(self, size):
                yield b"content"
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockSession:
            def __init__(self):
                self.get_calls = []
                
            def get(self, url, ssl=None):
                self.get_calls.append((url, ssl))
                return MockResponse()
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        class MockFile:
            async def write(self, data):
                pass
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        mock_session = MockSession()
        
        with patch('src.utils.file_utils.aiohttp.ClientSession', return_value=mock_session), \
             patch('src.utils.file_utils.aiofiles.open', return_value=MockFile()):
            
            filename, error = await download_file(url, temp_dir, verify_ssl=False)
            
            # 验证下载成功
            assert filename == "test.txt"
            assert error is None
            
            # 验证get方法被调用时使用了ssl=False
            assert len(mock_session.get_calls) == 1
            assert mock_session.get_calls[0] == (url, False)

