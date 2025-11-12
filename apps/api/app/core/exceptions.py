"""
Custom exceptions for the application.
"""


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class PermissionError(Exception):
    """Raised when user lacks required permissions."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ProcessingError(Exception):
    """Raised when processing fails."""
    pass

