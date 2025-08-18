import pytest
import tempfile
import os
from src.utils import network_restriction
from src.utils.network_restriction import (
    apply_network_restrictions, 
    restore_network_access, 
    temporary_network_access
)


class TestNetworkRestrictionContext:
    """Test network restriction context manager functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Ensure clean state before test
        restore_network_access()
        yield
        # Clean up after test
        restore_network_access()
    
    def test_temporary_network_access_context_manager(self):
        """Test that temporary_network_access context manager works correctly."""
        # Apply network restrictions
        apply_network_restrictions(enable_network=False)
        
        # Verify restrictions are active
        assert network_restriction._network_restrictions_active is True
        
        # Test context manager
        with temporary_network_access():
            # Inside context, restrictions should be temporarily disabled
            assert network_restriction._network_restrictions_active is False
        
        # After context, restrictions should be restored
        assert network_restriction._network_restrictions_active is True
    
    def test_nested_temporary_network_access(self):
        """Test nested temporary_network_access context managers."""
        # Apply network restrictions
        apply_network_restrictions(enable_network=False)
        
        # Verify restrictions are active
        assert network_restriction._network_restrictions_active is True
        
        # Test nested context managers
        with temporary_network_access():
            assert network_restriction._network_restrictions_active is False
            
            with temporary_network_access():
                assert network_restriction._network_restrictions_active is False
            
            # Should still be disabled after inner context
            assert network_restriction._network_restrictions_active is False
        
        # After all contexts, restrictions should be restored
        assert network_restriction._network_restrictions_active is True
    
    def test_temporary_network_access_with_exception(self):
        """Test that temporary_network_access properly restores state even with exceptions."""
        # Apply network restrictions
        apply_network_restrictions(enable_network=False)
        
        # Verify restrictions are active
        assert network_restriction._network_restrictions_active is True
        
        # Test context manager with exception
        try:
            with temporary_network_access():
                assert network_restriction._network_restrictions_active is False
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # After exception, restrictions should still be restored
        assert network_restriction._network_restrictions_active is True
    
    def test_temporary_network_access_without_initial_restrictions(self):
        """Test temporary_network_access when no restrictions are initially active."""
        # Ensure no restrictions are active
        restore_network_access()
        assert network_restriction._network_restrictions_active is False
        
        # Test context manager
        with temporary_network_access():
            # Should remain disabled
            assert network_restriction._network_restrictions_active is False
        
        # Should remain disabled after context
        assert network_restriction._network_restrictions_active is False