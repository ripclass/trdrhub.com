"""Compatibility shim for ``from app.models.user import User`` imports."""

from . import User, UserRole

__all__ = ["User", "UserRole"]
