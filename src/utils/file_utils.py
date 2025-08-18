"""File utility functions for the sandbox MCP server."""

import os
import aiohttp
import aiofiles
from urllib.parse import unquote
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
        # 文件下载在服务器进程中执行，不受 kernel 网络限制影响
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
                    
                    # 如果响应头中没有文件名，直接返回错误
                    if not filename:
                        error_msg = f"No filename could be determined from response headers for {url}"
                        return None, error_msg
                    
                    file_path = os.path.join(target_dir, filename)
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    logger.info(f"Downloaded file {filename} from {url}")
                    return filename, None
                else:
                    # HTTP错误时不提取文件名，直接返回None
                    error_msg = f"HTTP {response.status}: Failed to download {url}"
                    logger.error(error_msg)
                    return None, error_msg
    except Exception as e:
        # 完全禁止从URL提取文件名，异常时返回None
        error_msg = f"Failed to download {url}: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    if not filename:
        return "unnamed_file"
    
    # Remove invalid characters for most filesystems
    invalid_chars = r'[<>:"/\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Handle empty result
    if not sanitized:
        return "unnamed_file"
    
    # Limit length (keep extension if present)
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        if ext:
            # Keep extension, truncate name
            max_name_length = max_length - len(ext)
            sanitized = name[:max_name_length] + ext
        else:
            sanitized = sanitized[:max_length]
    
    return sanitized