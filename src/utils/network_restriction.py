"""Network access restriction utilities for kernel sessions."""

import socket
import urllib.request
import urllib.parse
import logging
from typing import Optional, List, Set
from functools import wraps

logger = logging.getLogger(__name__)

# Store original socket functions
_original_socket = socket.socket
_original_getaddrinfo = socket.getaddrinfo
_original_urlopen = urllib.request.urlopen

# Global state for network restrictions
_network_disabled = False
_network_restrictions_active = False
_allowed_domains: Set[str] = set()
_blocked_domains: Set[str] = set()


class NetworkAccessError(Exception):
    """Raised when network access is restricted."""
    pass


def _is_domain_allowed(hostname: str) -> bool:
    """Check if a domain is allowed for network access.
    
    Args:
        hostname: The hostname to check
        
    Returns:
        True if domain is allowed, False otherwise
    """
    if not hostname:
        return False
        
    # If no allowed domains specified, allow all (unless blocked)
    if not _allowed_domains:
        # Check if domain is in blocked list
        for blocked in _blocked_domains:
            if hostname == blocked or (blocked.startswith('.') and hostname.endswith(blocked)):
                return False
        return True
    
    # Check if domain is in allowed list
    for allowed in _allowed_domains:
        # Handle different matching patterns:
        # 1. Exact match: hostname == allowed
        # 2. Subdomain match: allowed starts with '.' and hostname ends with allowed
        # 3. Domain and subdomain match: allowed doesn't start with '.' but hostname is subdomain
        if hostname == allowed:
            match_found = True
        elif allowed.startswith('.') and (hostname.endswith(allowed) or hostname == allowed[1:]):
            match_found = True
        elif not allowed.startswith('.') and hostname.endswith('.' + allowed):
            match_found = True
        else:
            match_found = False
            
        if match_found:
            # Still check if it's blocked
            for blocked in _blocked_domains:
                if hostname == blocked or (blocked.startswith('.') and hostname.endswith(blocked)):
                    return False
            return True
    
    return False


def _restricted_socket(*args, **kwargs):
    """Restricted socket function that blocks network access."""
    if _network_disabled and _network_restrictions_active:
        logger.warning("Network access blocked: socket creation attempted")
        raise NetworkAccessError(
            "Network access is disabled for this session. "
            "Socket connections are not allowed."
        )
    return _original_socket(*args, **kwargs)


def _restricted_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Restricted getaddrinfo that checks domain allowlist."""
    if _network_disabled and _network_restrictions_active:
        logger.warning(f"Network access blocked: DNS lookup attempted for {host}")
        raise NetworkAccessError(
            f"Network access is disabled for this session. "
            f"DNS lookup for '{host}' is not allowed."
        )
    
    # Check domain restrictions even if network is enabled
    if not _is_domain_allowed(host):
        logger.warning(f"Domain access blocked: {host}")
        raise NetworkAccessError(
            f"Access to domain '{host}' is not allowed. "
            f"Only whitelisted domains are permitted."
        )
    
    return _original_getaddrinfo(host, port, family, type, proto, flags)


def _restricted_urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, **kwargs):
    """Restricted urlopen that checks URL access."""
    if _network_disabled and _network_restrictions_active:
        logger.warning(f"Network access blocked: HTTP request attempted to {url}")
        raise NetworkAccessError(
            "Network access is disabled for this session. "
            "HTTP requests are not allowed."
        )
    
    # Parse URL to check domain
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if hostname and not _is_domain_allowed(hostname):
            logger.warning(f"Domain access blocked: {hostname}")
            raise NetworkAccessError(
                f"Access to domain '{hostname}' is not allowed. "
                f"Only whitelisted domains are permitted."
            )
    except NetworkAccessError:
        # Re-raise NetworkAccessError as-is
        raise
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
        raise NetworkAccessError(f"Invalid URL: {url}")
    
    return _original_urlopen(url, data, timeout, **kwargs)


def disable_network_access() -> None:
    """Completely disable network access by monkey patching socket functions.
    
    This function replaces socket.socket, socket.getaddrinfo, and urllib.request.urlopen
    with restricted versions that raise NetworkAccessError when called.
    """
    global _network_disabled, _network_restrictions_active
    _network_disabled = True
    _network_restrictions_active = True
    
    # Monkey patch socket functions
    socket.socket = _restricted_socket
    socket.getaddrinfo = _restricted_getaddrinfo
    urllib.request.urlopen = _restricted_urlopen
    
    logger.info("Network access has been disabled for this session")


def enable_network_access(allowed_domains: Optional[List[str]] = None, 
                         blocked_domains: Optional[List[str]] = None) -> None:
    """Enable network access with optional domain restrictions.
    
    Args:
        allowed_domains: List of allowed domains (if None, all domains allowed)
        blocked_domains: List of blocked domains
    """
    global _network_disabled, _allowed_domains, _blocked_domains
    
    _network_disabled = False
    _allowed_domains = set(allowed_domains or [])
    _blocked_domains = set(blocked_domains or [])
    
    # Restore original functions but keep domain checking
    socket.socket = _original_socket
    socket.getaddrinfo = _restricted_getaddrinfo  # Keep domain checking
    urllib.request.urlopen = _restricted_urlopen  # Keep domain checking
    
    logger.info(
        f"Network access enabled. "
        f"Allowed domains: {_allowed_domains or 'all'}, "
        f"Blocked domains: {_blocked_domains or 'none'}"
    )


def restore_network_access() -> None:
    """Completely restore original network access without any restrictions."""
    global _network_disabled, _network_restrictions_active, _allowed_domains, _blocked_domains
    
    _network_disabled = False
    _network_restrictions_active = False
    _allowed_domains = set()
    _blocked_domains = set()
    
    # Restore all original functions
    socket.socket = _original_socket
    socket.getaddrinfo = _original_getaddrinfo
    urllib.request.urlopen = _original_urlopen
    
    logger.info("Network access fully restored")


def get_network_status() -> dict:
    """Get current network restriction status.
    
    Returns:
        Dictionary containing current network restriction settings
    """
    return {
        "network_disabled": _network_disabled,
        "allowed_domains": list(_allowed_domains),
        "blocked_domains": list(_blocked_domains)
    }


def apply_network_restrictions(enable_network: bool = False,
                             allowed_domains: Optional[List[str]] = None,
                             blocked_domains: Optional[List[str]] = None) -> None:
    """Apply network restrictions based on configuration.
    
    Args:
        enable_network: Whether to enable network access
        allowed_domains: List of allowed domains
        blocked_domains: List of blocked domains
    """
    global _network_restrictions_active
    
    # Activate network restrictions
    _network_restrictions_active = True
    
    if not enable_network:
        disable_network_access()
    else:
        enable_network_access(allowed_domains, blocked_domains)