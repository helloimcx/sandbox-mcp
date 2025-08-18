"""Kernel management for the sandbox MCP server."""

import time
from typing import Optional
from jupyter_client.manager import AsyncKernelManager
from jupyter_client import AsyncKernelClient
import logging

from config.config import settings
from utils.network_restriction import apply_network_restrictions, temporary_network_access

logger = logging.getLogger(__name__)


class KernelSession:
    """Represents a kernel session."""
    
    def __init__(self, session_id: str, kernel_manager: AsyncKernelManager):
        self.session_id = session_id
        self.kernel_manager = kernel_manager
        self.kernel_client: Optional[AsyncKernelClient] = None
        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_busy = False
        self.execution_count = 0
    
    async def start(self) -> None:
        """Start the kernel and client."""
        # Use temporary network access for kernel startup (port allocation)
        with temporary_network_access():
            await self.kernel_manager.start_kernel(cwd=self.kernel_manager.cwd)
            self.kernel_client = self.kernel_manager.client()
            self.kernel_client.start_channels()
            await self.kernel_client.wait_for_ready()
        
        # Apply network restrictions only if explicitly configured
        if hasattr(settings, 'enable_network_access'):
            apply_network_restrictions(
                enable_network=settings.enable_network_access,
                allowed_domains=settings.allowed_domains,
                blocked_domains=settings.blocked_domains
            )
            logger.info(f"Network restrictions applied for session {self.session_id}: "
                       f"enabled={settings.enable_network_access}")
        else:
            logger.info(f"Network restrictions not configured for session {self.session_id}")
        
        # 重新实现字体配置，确保matplotlib图片能被正确捕获
        font_setup_code = """import matplotlib.pyplot as plt
from mplfonts import use_font

# 配置中文字体支持
try:
    use_font('Noto Sans CJK SC')
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
"""
        
        try:
            # 执行字体配置代码（静默执行）并等待完成
            msg_id = self.kernel_client.execute(font_setup_code, silent=True)
            while True:
                reply = await self.kernel_client.get_iopub_msg()
                if reply['msg_type'] == 'status' and reply['content'].get('execution_state') == 'idle':
                    break
            logger.info(f"Font configuration executed for kernel session {self.session_id}")
        except Exception as e:
            logger.warning(f"Failed to execute font configuration for session {self.session_id}: {e}")
        
        logger.info(f"Kernel session {self.session_id} started")
    
    async def stop(self) -> None:
        """Stop the kernel and client."""
        if self.kernel_client:
            self.kernel_client.stop_channels()
        await self.kernel_manager.shutdown_kernel()
        
        # Cleanup session directory
        import shutil
        try:
            if hasattr(self.kernel_manager, 'cwd') and self.kernel_manager.cwd:
                shutil.rmtree(self.kernel_manager.cwd)
                logger.info(f"Cleaned up session directory: {self.kernel_manager.cwd}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directory: {e}")
        
        logger.info(f"Kernel session {self.session_id} stopped")
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
    
    def is_idle_timeout(self) -> bool:
        """Check if session has timed out."""
        return time.time() - self.last_activity > settings.kernel_timeout


