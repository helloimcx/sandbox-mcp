"""Unit tests for network restriction functionality."""

import pytest
import socket
import urllib.request
from unittest.mock import patch, MagicMock

from utils.network_restriction import (
    disable_network_access,
    enable_network_access,
    restore_network_access,
    apply_network_restrictions,
    get_network_status,
    NetworkAccessError,
    _is_domain_allowed
)


class TestNetworkRestriction:
    """Test network restriction functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Restore network access before each test
        restore_network_access()
        # Import and ensure global variables are properly initialized
        import utils.network_restriction as nr
        nr._network_restrictions_active = False
        nr._network_disabled = False
        nr._allowed_domains = set()
        nr._blocked_domains = set()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Restore network access after each test
        restore_network_access()
    
    def test_disable_network_access_blocks_socket_creation(self):
        """Test that disabling network access blocks socket creation."""
        # Arrange
        disable_network_access()
        
        # Act & Assert
        with pytest.raises(NetworkAccessError, match="Network access is disabled"):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def test_disable_network_access_blocks_dns_lookup(self):
        """Test that disabling network access blocks DNS lookups."""
        # Arrange
        disable_network_access()
        
        # Act & Assert
        with pytest.raises(NetworkAccessError, match="Network access is disabled"):
            socket.getaddrinfo('google.com', 80)
    
    def test_disable_network_access_blocks_urllib_requests(self):
        """Test that disabling network access blocks urllib requests."""
        # Arrange
        disable_network_access()
        
        # Act & Assert
        with pytest.raises(NetworkAccessError, match="Network access is disabled"):
            urllib.request.urlopen('http://google.com')
    
    def test_enable_network_access_allows_all_domains_by_default(self):
        """Test that enabling network access without restrictions allows all domains."""
        # Arrange
        enable_network_access()
        
        # Act - This should not raise an exception
        # We mock the actual network call to avoid real network requests in tests
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = []
            socket.getaddrinfo('google.com', 80)
            mock_getaddrinfo.assert_called_once()
    
    def test_enable_network_access_with_allowed_domains(self):
        """Test that enabling network access with allowed domains works correctly."""
        # Arrange
        allowed_domains = ['google.com', 'github.com']
        enable_network_access(allowed_domains=allowed_domains)
        
        # Act & Assert - Allowed domain should work
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = []
            socket.getaddrinfo('google.com', 80)
            mock_getaddrinfo.assert_called_once()
        
        # Act & Assert - Blocked domain should fail
        with pytest.raises(NetworkAccessError, match="not allowed"):
            socket.getaddrinfo('facebook.com', 80)
    
    def test_enable_network_access_with_blocked_domains(self):
        """Test that enabling network access with blocked domains works correctly."""
        # Arrange
        blocked_domains = ['facebook.com', 'twitter.com']
        enable_network_access(blocked_domains=blocked_domains)
        
        # Act & Assert - Allowed domain should work
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = []
            socket.getaddrinfo('google.com', 80)
            mock_getaddrinfo.assert_called_once()
        
        # Act & Assert - Blocked domain should fail
        with pytest.raises(NetworkAccessError, match="not allowed"):
            socket.getaddrinfo('facebook.com', 80)
    
    def test_urllib_domain_restrictions(self):
        """Test that urllib requests respect domain restrictions."""
        # Arrange
        allowed_domains = ['httpbin.org']
        enable_network_access(allowed_domains=allowed_domains)
        
        # Act & Assert - Allowed domain should work
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.return_value = MagicMock()
            urllib.request.urlopen('http://httpbin.org/get')
            mock_urlopen.assert_called_once()
        
        # Act & Assert - Blocked domain should fail
        with pytest.raises(NetworkAccessError, match="Access to domain .* is not allowed"):
            urllib.request.urlopen('http://google.com')
    
    def test_domain_matching_logic(self):
        """Test the domain matching logic."""
        # Test exact match
        assert _is_domain_allowed('google.com') == True  # No restrictions
        
        # Test with allowed domains
        global _allowed_domains
        from utils.network_restriction import _allowed_domains
        _allowed_domains.add('google.com')
        assert _is_domain_allowed('google.com') == True
        assert _is_domain_allowed('facebook.com') == False
        
        # Test subdomain matching
        _allowed_domains.clear()
        _allowed_domains.add('.google.com')
        assert _is_domain_allowed('www.google.com') == True
        assert _is_domain_allowed('api.google.com') == True
        assert _is_domain_allowed('google.com') == True
        assert _is_domain_allowed('facebook.com') == False
    
    def test_get_network_status(self):
        """Test getting network status information."""
        # Test disabled state
        disable_network_access()
        status = get_network_status()
        assert status['network_disabled'] == True
        assert status['allowed_domains'] == []
        assert status['blocked_domains'] == []
        
        # Test enabled state with restrictions
        allowed = ['google.com']
        blocked = ['facebook.com']
        enable_network_access(allowed_domains=allowed, blocked_domains=blocked)
        status = get_network_status()
        assert status['network_disabled'] == False
        assert set(status['allowed_domains']) == set(allowed)
        assert set(status['blocked_domains']) == set(blocked)
    
    def test_apply_network_restrictions_disable(self):
        """Test applying network restrictions with disabled network."""
        # Arrange & Act
        apply_network_restrictions(enable_network=False)
        
        # Assert
        status = get_network_status()
        assert status['network_disabled'] == True
        
        with pytest.raises(NetworkAccessError):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    def test_apply_network_restrictions_enable_with_domains(self):
        """Test applying network restrictions with enabled network and domain restrictions."""
        # Arrange & Act
        allowed = ['google.com']
        blocked = ['facebook.com']
        apply_network_restrictions(
            enable_network=True,
            allowed_domains=allowed,
            blocked_domains=blocked
        )
        
        # Assert
        status = get_network_status()
        assert status['network_disabled'] == False
        assert set(status['allowed_domains']) == set(allowed)
        assert set(status['blocked_domains']) == set(blocked)
        
        # Test domain restrictions
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = []
            socket.getaddrinfo('google.com', 80)  # Should work
            mock_getaddrinfo.assert_called_once()
        
        with pytest.raises(NetworkAccessError):
            socket.getaddrinfo('facebook.com', 80)  # Should fail
    
    def test_restore_network_access(self):
        """Test that restore_network_access completely removes all restrictions."""
        # Arrange - Set up restrictions
        disable_network_access()
        
        # Verify restrictions are in place
        with pytest.raises(NetworkAccessError):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Act
        restore_network_access()
        
        # Assert - Network should be fully restored
        status = get_network_status()
        assert status['network_disabled'] == False
        assert status['allowed_domains'] == []
        assert status['blocked_domains'] == []
        
        # Should be able to create socket without restrictions
        # (We don't actually create a real socket to avoid network dependencies)
        with patch('socket.socket') as mock_socket:
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            mock_socket.assert_called_once()


class TestNetworkRestrictionIntegration:
    """Integration tests for network restriction with kernel sessions."""
    
    def setup_method(self):
        """Setup for each test method."""
        restore_network_access()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        restore_network_access()
    
    @pytest.mark.asyncio
    async def test_network_restriction_in_kernel_session(self):
        """Test that network restrictions are applied in kernel sessions."""
        # This test would require a full kernel session setup
        # For now, we test the configuration application
        
        from config.config import settings
        
        # Mock settings
        original_enable = settings.enable_network_access
        original_allowed = settings.allowed_domains
        original_blocked = settings.blocked_domains
        
        try:
            # Configure network restrictions
            settings.enable_network_access = False
            settings.allowed_domains = []
            settings.blocked_domains = []
            
            # Apply restrictions
            apply_network_restrictions(
                enable_network=settings.enable_network_access,
                allowed_domains=settings.allowed_domains,
                blocked_domains=settings.blocked_domains
            )
            
            # Verify restrictions are applied
            status = get_network_status()
            assert status['network_disabled'] == True
            
            with pytest.raises(NetworkAccessError):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        finally:
            # Restore original settings
            settings.enable_network_access = original_enable
            settings.allowed_domains = original_allowed
            settings.blocked_domains = original_blocked
            restore_network_access()