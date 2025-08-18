"""Global test configuration."""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Network restriction functionality has been removed
# Tests now run without network restrictions by default