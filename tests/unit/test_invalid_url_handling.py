"""测试无效URL处理的单元测试"""

import pytest
import tempfile
import shutil
from unittest.mock import patch, AsyncMock

from src.utils.file_utils import download_file
from src.services.kernel_manager import KernelManagerService
from src.schema.models import FileItem


class TestInvalidUrlHandling:
    """测试无效URL处理的测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_download_file_with_invalid_url_returns_error(self, temp_dir):
        """测试下载无效URL时返回错误信息"""
        invalid_url = "https://invalid-domain-that-does-not-exist.com/file.txt"
        
        filename, error = await download_file(invalid_url, temp_dir, timeout=5)
        
        # 应该返回错误信息
        assert error is not None
        assert "Failed to download" in error
        assert invalid_url in error
        
        # 应该返回从URL提取的文件名
        assert filename == "file.txt"
    
    @pytest.mark.asyncio
    async def test_download_file_with_malformed_url_returns_error(self, temp_dir):
        """测试下载格式错误的URL时返回错误信息"""
        malformed_url = "not-a-valid-url"
        
        filename, error = await download_file(malformed_url, temp_dir, timeout=5)
        
        # 应该返回错误信息
        assert error is not None
        assert "Failed to download" in error
        assert malformed_url in error
        
        # 应该返回从URL解析的文件名（对于无效URL，会是URL本身）
        assert filename == malformed_url
    
    @pytest.mark.asyncio
    async def test_download_file_with_404_url_returns_error(self, temp_dir):
        """测试下载404 URL时返回HTTP错误信息"""
        not_found_url = "https://httpbin.org/status/404"
        
        filename, error = await download_file(not_found_url, temp_dir, timeout=10)
        
        # 应该返回错误信息（可能是HTTP错误或连接错误）
        assert error is not None
        assert "Failed to download" in error
        assert not_found_url in error
        
        # 应该返回从URL提取的文件名
        assert filename == "404"
    
    @pytest.mark.asyncio
    async def test_download_file_with_timeout_returns_error(self, temp_dir):
        """测试下载超时时返回错误信息"""
        # 使用一个会超时的URL（httpbin的delay端点）
        timeout_url = "https://httpbin.org/delay/10"
        
        filename, error = await download_file(timeout_url, temp_dir, timeout=1)
        
        # 应该返回超时错误信息
        assert error is not None
        assert "Failed to download" in error
        assert timeout_url in error
        
        # 应该返回从URL提取的文件名
        assert filename == "10"
    
    @pytest.mark.asyncio
    async def test_process_file_urls_with_invalid_urls_returns_errors(self):
        """测试处理无效文件URL时返回错误信息"""
        kernel_manager = KernelManagerService()
        
        invalid_urls = [
            "https://invalid-domain.com/file1.txt",
            "not-a-url",
            "https://httpbin.org/status/404"
        ]
        
        # 直接测试_process_file_urls方法
        downloaded_files = []
        errors = await kernel_manager._process_file_urls(invalid_urls, "/tmp/test", timeout=5, downloaded_files=downloaded_files)
        
        # 应该没有下载成功的文件
        assert len(downloaded_files) == 0
        
        # 应该有错误信息，每个无效URL对应一个错误
        assert len(errors) == len(invalid_urls)
        
        # 检查错误信息内容
        for i, error in enumerate(errors):
            assert "Failed to download" in error
            assert invalid_urls[i] in error
    
    @pytest.mark.asyncio
    async def test_process_files_with_id_with_invalid_files_returns_errors(self, temp_dir):
        """测试处理无效文件（带ID）时返回错误信息"""
        kernel_manager = KernelManagerService()
        
        invalid_files = [
            FileItem(id="file1", url="https://invalid-domain.com/file1.txt"),
            FileItem(id="file2", url="not-a-url"),
            FileItem(id="file3", url="https://httpbin.org/status/500")
        ]
        
        # 创建一个临时的session config
        from src.config.session_config import SessionFileConfig
        session_config = SessionFileConfig(temp_dir)
        
        # 直接测试_process_files_with_id方法
        downloaded_files = []
        errors = await kernel_manager._process_files_with_id(
            invalid_files, session_config, temp_dir, timeout=5, downloaded_files=downloaded_files
        )
        
        # 应该没有下载成功的文件
        assert len(downloaded_files) == 0
        
        # 应该有错误信息，每个无效文件对应一个错误
        assert len(errors) == len(invalid_files)
        
        # 检查错误信息内容
        for i, error in enumerate(errors):
            assert f"Failed to download file {invalid_files[i].id}" in error
            assert "Failed to download" in error
    
    @pytest.mark.asyncio
    async def test_process_mixed_valid_invalid_urls(self):
        """测试处理有效和无效URL的混合情况"""
        kernel_manager = KernelManagerService()
        
        mixed_urls = [
            "https://httpbin.org/json",  # 有效URL（可能因网络问题失败）
            "https://invalid-domain.com/file.txt",  # 无效URL
            "https://httpbin.org/status/404"  # 404 URL
        ]
        
        # 直接测试_process_file_urls方法
        downloaded_files = []
        errors = await kernel_manager._process_file_urls(mixed_urls, "/tmp/test", timeout=10, downloaded_files=downloaded_files)
        
        # 由于网络环境的不确定性，我们主要验证错误处理机制
        # 至少应该有一些错误（无效域名和404）
        assert len(errors) >= 2
        
        # 检查错误信息
        assert any("invalid-domain.com" in error for error in errors)
        assert any("Failed to download" in error for error in errors)
        
        # 验证下载文件数量和错误数量的总和等于URL数量
        assert len(downloaded_files) + len(errors) == len(mixed_urls)