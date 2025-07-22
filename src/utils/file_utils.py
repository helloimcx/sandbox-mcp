"""File utility functions for the sandbox MCP server."""

import os
import time
import aiohttp
import aiofiles
from urllib.parse import urlparse
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


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
    try:
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = f"downloaded_file_{int(time.time())}"
        
        file_path = os.path.join(target_dir, filename)
        
        # 创建SSL上下文，可选择禁用证书验证
        ssl_context = None
        if not verify_ssl:
            ssl_context = False  # aiohttp中使用False表示禁用SSL验证
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url, ssl=ssl_context) as response:
                if response.status == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    logger.info(f"Downloaded file {filename} from {url}")
                    return filename, None
                else:
                    error_msg = f"HTTP {response.status}: Failed to download {url}"
                    logger.error(error_msg)
                    return filename, error_msg
    except Exception as e:
        error_msg = f"Failed to download {url}: {str(e)}"
        logger.error(error_msg)
        return filename if 'filename' in locals() else "unknown_file", error_msg