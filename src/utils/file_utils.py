"""File utility functions for the sandbox MCP server."""

import os
import time
import aiohttp
import aiofiles
from urllib.parse import urlparse, unquote
from pathlib import Path
from typing import Tuple, Optional
import logging
import re

logger = logging.getLogger(__name__)


def _extract_filename_from_content_disposition(content_disposition: str) -> Optional[str]:
    """Extract filename from Content-Disposition header.
    
    Args:
        content_disposition: Content-Disposition header value
        
    Returns:
        Extracted filename or None if not found
    """
    if not content_disposition:
        return None
    
    # Try to find filename* parameter (RFC 5987)
    filename_star_match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", content_disposition, re.IGNORECASE)
    if filename_star_match:
        filename = unquote(filename_star_match.group(1))
        return filename
    
    # Try to find filename parameter
    filename_match = re.search(r'filename="?([^"\s;]+)"?', content_disposition, re.IGNORECASE)
    if filename_match:
        filename = filename_match.group(1)
        return filename
    
    return None


def _get_filename_from_url(url: str) -> str:
    """Extract filename from URL path.
    
    Args:
        url: File URL
        
    Returns:
        Extracted filename or generated filename if not found
    """
    parsed_url = urlparse(url)
    filename = Path(parsed_url.path).name
    
    # Remove query parameters and fragments from filename
    if filename and '?' in filename:
        filename = filename.split('?')[0]
    if filename and '#' in filename:
        filename = filename.split('#')[0]
    
    # If still no filename, generate one
    if not filename or filename == '/':
        filename = f"downloaded_file_{int(time.time())}"
    
    return filename


async def download_file(url: str, target_dir: str, timeout: int = 30, verify_ssl: bool = True) -> Tuple[str, Optional[str]]:
    """Download a file from URL to target directory.
    
    Args:
        url: File URL to download
        target_dir: Target directory to save the file
        timeout: Download timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        Tuple of (filename, error_message). error_message is None if successful.
    """
    filename = None
    try:
        # 创建SSL上下文，可选择禁用证书验证
        ssl_context = None
        if not verify_ssl:
            ssl_context = False  # aiohttp中使用False表示禁用SSL验证
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    # 尝试从响应头获取文件名
                    content_disposition = response.headers.get('Content-Disposition')
                    filename = _extract_filename_from_content_disposition(content_disposition)
                    
                    # 如果响应头中没有文件名，从URL中提取
                    if not filename:
                        filename = _get_filename_from_url(url)
                    
                    file_path = os.path.join(target_dir, filename)
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    logger.info(f"Downloaded file {filename} from {url}")
                    return filename, None
                else:
                    # 即使下载失败，也尝试获取文件名用于错误报告
                    if not filename:
                        filename = _get_filename_from_url(url)
                    error_msg = f"HTTP {response.status}: Failed to download {url}"
                    logger.error(error_msg)
                    return filename, error_msg
    except Exception as e:
        # 如果还没有文件名，从URL中提取
        if not filename:
            filename = _get_filename_from_url(url)
        error_msg = f"Failed to download {url}: {str(e)}"
        logger.error(error_msg)
        return filename, error_msg