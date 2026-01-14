"""
Shared utilities for DGX Spark services.

Modules:
    auth: Authentication and rate limiting
"""

from .auth import add_auth_middleware, require_auth, get_client_ip

__all__ = ["add_auth_middleware", "require_auth", "get_client_ip"]
