"""
Compliance Rule Handlers

Python handlers for complex validation logic that cannot be expressed in DSL.
Each handler module must implement a validate(lc_document) function that returns:
{
    "status": "pass" | "fail" | "warning" | "error",
    "details": "Detailed explanation of result",
    "field_location": "Optional field path",
    "suggested_fix": "Optional suggestion for fixing the issue"
}
"""

__version__ = "1.0.0"