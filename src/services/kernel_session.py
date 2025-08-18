"""Kernel management for the sandbox MCP server."""

import time
from typing import Optional
from jupyter_client.manager import AsyncKernelManager
from jupyter_client import AsyncKernelClient
import logging

from config.config import settings

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
        await self.kernel_manager.start_kernel(cwd=self.kernel_manager.cwd)
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        await self.kernel_client.wait_for_ready()
        
        # Apply network restrictions only in kernel if explicitly configured
        if hasattr(settings, 'enable_network_access'):
            # If network access is disabled, execute restriction code in the kernel
            if not settings.enable_network_access:
                await self._apply_kernel_network_restrictions()
            
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
    
    async def _apply_kernel_network_restrictions(self) -> None:
        """Apply network restrictions directly in the kernel by executing restriction code."""
        # 简单高效的socket阻断方法 - 阻止所有基于socket的网络访问
        simple_restriction_code = '''
# 简单高效的网络限制方法 - 直接阻断socket连接
import socket

def disabled_socket(*args, **kwargs):
    """替换socket.socket函数，阻止所有网络连接。"""
    raise OSError("Network access is disabled for security reasons")

# 替换socket.socket函数
socket.socket = disabled_socket

print("Network restrictions applied in kernel (simple socket blocking)")
'''
        
        try:
            # Execute network restriction code in the kernel
            msg_id = self.kernel_client.execute(simple_restriction_code, silent=True)
            
            # Wait for execution to complete
            while True:
                reply = await self.kernel_client.get_iopub_msg()
                if reply['msg_type'] == 'status' and reply['content'].get('execution_state') == 'idle':
                    break
                elif reply['msg_type'] == 'stream' and reply['content'].get('name') == 'stdout':
                    if 'Network restrictions applied in kernel (simple socket blocking)' in reply['content'].get('text', ''):
                        logger.info(f"Network restrictions successfully applied in kernel {self.session_id}")
                elif reply['msg_type'] == 'error':
                    logger.error(f"Error applying network restrictions in kernel {self.session_id}: {reply['content']}")
                    
        except Exception as e:
            logger.error(f"Failed to apply network restrictions in kernel {self.session_id}: {e}")
    
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


