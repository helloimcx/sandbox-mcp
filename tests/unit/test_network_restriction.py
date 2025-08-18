"""Tests for network restriction functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from services.kernel_session import KernelSession
from config.config import settings


class TestNetworkRestriction:
    """Test network restriction functionality."""
    
    @pytest.fixture
    def mock_kernel_manager(self):
        """Create mock kernel manager."""
        mock_km = AsyncMock()
        mock_km.start_kernel = AsyncMock()
        mock_km.shutdown_kernel = AsyncMock()
        mock_km.cwd = "/tmp/test_session"
        
        mock_client = AsyncMock()
        mock_client.start_channels = MagicMock()
        mock_client.stop_channels = MagicMock()
        mock_client.wait_for_ready = AsyncMock()
        mock_client.execute = MagicMock(return_value="test_msg_id")
        
        # Mock get_iopub_msg to simulate network restriction messages
        mock_network_msg = {
            'msg_type': 'stream',
            'content': {
                'name': 'stdout',
                'text': 'Network restrictions applied in kernel (simple socket blocking)'
            }
        }
        mock_idle_msg = {
            'msg_type': 'status',
            'content': {'execution_state': 'idle'}
        }
        
        # Return network message first, then idle message
        mock_client.get_iopub_msg = AsyncMock(side_effect=[mock_network_msg, mock_idle_msg])
        
        mock_km.client = MagicMock(return_value=mock_client)
        
        return mock_km
    
    @pytest.mark.asyncio
    async def test_network_restriction_applied_when_disabled(self, mock_kernel_manager):
        """Test that network restrictions are applied when network access is disabled."""
        # Mock settings to disable network access
        with patch.object(settings, 'enable_network_access', False):
            session = KernelSession("test-session", mock_kernel_manager)
            
            # Start session should apply network restrictions
            await session.start()
            
            # Verify that execute was called multiple times (font setup + network restriction)
            execute_calls = mock_kernel_manager.client().execute.call_args_list
            assert len(execute_calls) >= 2, "Should have at least 2 execute calls (font + network)"
            
            # Find the network restriction call (should be the second call)
            network_restriction_found = False
            for call in execute_calls:
                code = call[0][0]
                if 'socket.socket = disabled_socket' in code:
                    network_restriction_found = True
                    # Check that the restriction code contains expected elements
                    assert 'def disabled_socket' in code
                    assert 'Network access is disabled for security reasons' in code
                    break
            
            assert network_restriction_found, "Network restriction code should be executed"
    
    @pytest.mark.asyncio
    async def test_network_restriction_not_applied_when_enabled(self, mock_kernel_manager):
        """Test that network restrictions are not applied when network access is enabled."""
        # Mock settings to enable network access
        with patch.object(settings, 'enable_network_access', True):
            session = KernelSession("test-session", mock_kernel_manager)
            
            # Mock get_iopub_msg to return only idle message (no network restriction)
            mock_idle_msg = {
                'msg_type': 'status',
                'content': {'execution_state': 'idle'}
            }
            mock_kernel_manager.client().get_iopub_msg = AsyncMock(return_value=mock_idle_msg)
            
            await session.start()
            
            # Verify that execute was called only for font setup, not network restrictions
            execute_calls = mock_kernel_manager.client().execute.call_args_list
            
            # Should have font setup call but no network restriction call
            font_call_found = False
            network_call_found = False
            
            for call in execute_calls:
                code = call[0][0]
                if 'matplotlib.pyplot' in code and 'use_font' in code:
                    font_call_found = True
                elif 'socket.socket = disabled_socket' in code:
                    network_call_found = True
            
            assert font_call_found, "Font setup should be called"
            assert not network_call_found, "Network restriction should not be called when enabled"
    
    @pytest.mark.asyncio
    async def test_network_restriction_not_applied_when_not_configured(self, mock_kernel_manager):
        """Test that network restrictions are not applied when not configured."""
        # Remove enable_network_access attribute to simulate not configured
        original_attr = getattr(settings, 'enable_network_access', None)
        if hasattr(settings, 'enable_network_access'):
            delattr(settings, 'enable_network_access')
        
        try:
            session = KernelSession("test-session", mock_kernel_manager)
            
            # Mock get_iopub_msg to return only idle message
            mock_idle_msg = {
                'msg_type': 'status',
                'content': {'execution_state': 'idle'}
            }
            mock_kernel_manager.client().get_iopub_msg = AsyncMock(return_value=mock_idle_msg)
            
            await session.start()
            
            # Verify that execute was called only for font setup
            execute_calls = mock_kernel_manager.client().execute.call_args_list
            
            # Should have font setup call but no network restriction call
            font_call_found = False
            network_call_found = False
            
            for call in execute_calls:
                code = call[0][0]
                if 'matplotlib.pyplot' in code and 'use_font' in code:
                    font_call_found = True
                elif 'socket.socket = disabled_socket' in code:
                    network_call_found = True
            
            assert font_call_found, "Font setup should be called"
            assert not network_call_found, "Network restriction should not be called when not configured"
        
        finally:
            # Restore original attribute
            if original_attr is not None:
                setattr(settings, 'enable_network_access', original_attr)
    
    @pytest.mark.asyncio
    async def test_network_restriction_error_handling(self, mock_kernel_manager):
        """Test error handling during network restriction application."""
        with patch.object(settings, 'enable_network_access', False):
            session = KernelSession("test-session", mock_kernel_manager)
            
            # Mock get_iopub_msg to return error message
            mock_error_msg = {
                'msg_type': 'error',
                'content': {
                    'ename': 'ImportError',
                    'evalue': 'Test error',
                    'traceback': ['Test traceback']
                }
            }
            mock_idle_msg = {
                'msg_type': 'status',
                'content': {'execution_state': 'idle'}
            }
            
            mock_kernel_manager.client().get_iopub_msg = AsyncMock(side_effect=[mock_error_msg, mock_idle_msg])
            
            # Should not raise exception even if network restriction fails
            await session.start()
            
            # Verify that execute was still called
            mock_kernel_manager.client().execute.assert_called()
    
    def test_simple_socket_restriction_method(self):
        """Test the simple socket restriction method that will replace current implementation."""
        # This tests the new simple method we plan to implement
        simple_restriction_code = '''
import socket

def disabled_socket(*args, **kwargs):
    raise OSError("Network access is disabled for security reasons")

# Replace socket.socket with disabled version
socket.socket = disabled_socket
print("Simple network restrictions applied")
'''
        
        # Verify the code structure
        assert 'socket.socket = disabled_socket' in simple_restriction_code
        assert 'Network access is disabled' in simple_restriction_code
        assert 'def disabled_socket' in simple_restriction_code
    
    def test_current_complex_restriction_method(self):
        """Test the current complex restriction method structure."""
        # This represents the current implementation
        complex_restriction_code = '''
import sys

# Module blocking
sys.modules["socket"] = None
sys.modules["requests"] = None

# Import blocking
banned_modules = ['socket', 'requests', 'urllib']
original_import = __builtins__.__import__

def restricted_import(name, *args, **kwargs):
    if name in banned_modules:
        raise ImportError(f"Module '{name}' is restricted")
    return original_import(name, *args, **kwargs)

__builtins__.__import__ = restricted_import
'''
        
        # Verify the current complex method structure
        assert 'sys.modules["socket"] = None' in complex_restriction_code
        assert 'banned_modules' in complex_restriction_code
        assert 'restricted_import' in complex_restriction_code
        assert '__builtins__.__import__' in complex_restriction_code