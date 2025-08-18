"""Global test configuration."""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

@pytest.fixture(autouse=True)
def disable_network_restrictions(request):
    """Automatically disable network restrictions for all tests except network restriction tests."""
    # Check if this is a network restriction test or performance test
    test_file_path = str(request.fspath) if hasattr(request, 'fspath') else ''
    is_network_test = 'test_network_restriction' in test_file_path
    is_performance_test = '/performance/' in test_file_path
    
    if not is_network_test and not is_performance_test:
        # Disable network restrictions for non-network tests and non-performance tests
        try:
            from utils.network_restriction import restore_network_access
            restore_network_access()
        except ImportError:
            pass
    
    yield
    
    # Clean up after test only for non-network restriction tests and non-performance tests
    if not is_network_test and not is_performance_test:
        try:
            from utils.network_restriction import restore_network_access
            restore_network_access()
        except ImportError:
            pass