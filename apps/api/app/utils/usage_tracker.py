"""
Usage Tracking Decorator

Decorator and utilities for automatic usage tracking on billable endpoints.

Usage:
    from app.utils.usage_tracker import track_usage
    
    @router.post("/validate")
    @track_usage(operation="lc_validation", tool="lcopilot")
    async def validate_lc(request: Request, ...):
        ...
"""

import functools
import logging
from typing import Optional, Callable, Any
from uuid import UUID

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def track_usage(
    operation: str,
    tool: str,
    quantity: int = 1,
    quantity_from_request: Optional[str] = None,
    check_limit_first: bool = True,
    description: Optional[str] = None
):
    """
    Decorator to automatically track usage for billable endpoints.
    
    Args:
        operation: Type of operation (lc_validation, price_check, etc.)
        tool: Tool identifier (lcopilot, price_verify, etc.)
        quantity: Fixed quantity to track (default 1)
        quantity_from_request: Path to extract quantity from request body
        check_limit_first: Whether to check limits before execution
        description: Description template for log entry
        
    Example:
        @track_usage(operation="lc_validation", tool="lcopilot")
        async def validate_lc(...):
            ...
            
        @track_usage(
            operation="price_check", 
            tool="price_verify",
            quantity_from_request="items.length"
        )
        async def batch_verify(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            request: Optional[Request] = kwargs.get("request")
            db: Optional[Session] = kwargs.get("db")
            current_user = kwargs.get("current_user")
            
            # Skip tracking if missing required dependencies
            if not current_user or not hasattr(current_user, "company_id") or not current_user.company_id:
                logger.debug(f"Skipping usage tracking: no company_id for user")
                return await func(*args, **kwargs)
            
            if not db:
                logger.warning(f"Skipping usage tracking: no db session")
                return await func(*args, **kwargs)
            
            # Import here to avoid circular imports
            from app.services.usage_service import get_usage_service
            
            service = get_usage_service(db)
            company_id = current_user.company_id
            user_id = current_user.id if hasattr(current_user, "id") else None
            
            # Determine quantity
            actual_quantity = quantity
            if quantity_from_request and request:
                try:
                    body = await request.json() if hasattr(request, "json") else {}
                    # Navigate path like "items.length" or "documents"
                    parts = quantity_from_request.split(".")
                    value = body
                    for part in parts:
                        if part == "length" and isinstance(value, list):
                            value = len(value)
                        elif isinstance(value, dict):
                            value = value.get(part, 1)
                    actual_quantity = int(value) if value else quantity
                except Exception as e:
                    logger.debug(f"Could not extract quantity from request: {e}")
            
            # Check limit first if enabled
            if check_limit_first:
                try:
                    allowed, message, info = await service.check_limit(
                        company_id, operation, actual_quantity
                    )
                    if not allowed:
                        raise HTTPException(
                            status_code=402,  # Payment Required
                            detail=f"Usage limit exceeded: {message}"
                        )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning(f"Failed to check limit: {e}")
            
            # Execute the actual function
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                # Don't record usage if operation failed
                raise
            
            # Record usage after successful execution
            try:
                desc = description or f"{operation} via {tool}"
                log_data = {
                    "endpoint": func.__name__,
                    "tool": tool
                }
                
                success, msg, overage = await service.record_usage(
                    company_id=company_id,
                    user_id=user_id,
                    operation=operation,
                    tool=tool,
                    quantity=actual_quantity,
                    log_data=log_data,
                    description=desc
                )
                
                if not success:
                    logger.warning(f"Failed to record usage: {msg}")
                    
            except Exception as e:
                # Don't fail the request if usage recording fails
                logger.error(f"Error recording usage: {e}")
            
            return result
        
        return wrapper
    return decorator


async def record_usage_manual(
    db: Session,
    company_id: UUID,
    user_id: Optional[UUID],
    operation: str,
    tool: str,
    quantity: int = 1,
    log_data: Optional[dict] = None,
    description: Optional[str] = None
) -> bool:
    """
    Manually record usage when decorator approach isn't suitable.
    
    Use this for:
    - Background jobs
    - Batch operations with variable quantities
    - Operations spanning multiple endpoints
    
    Returns:
        True if recorded successfully, False otherwise
    """
    try:
        from app.services.usage_service import get_usage_service
        
        service = get_usage_service(db)
        success, message, _ = await service.record_usage(
            company_id=company_id,
            user_id=user_id,
            operation=operation,
            tool=tool,
            quantity=quantity,
            log_data=log_data,
            description=description
        )
        return success
        
    except Exception as e:
        logger.error(f"Failed to record manual usage: {e}")
        return False


async def check_usage_limit(
    db: Session,
    company_id: UUID,
    operation: str,
    quantity: int = 1
) -> tuple[bool, str, dict]:
    """
    Check if operation is allowed before executing.
    
    Use this for pre-flight checks in complex workflows.
    
    Returns:
        Tuple of (allowed, message, usage_info)
    """
    try:
        from app.services.usage_service import get_usage_service
        
        service = get_usage_service(db)
        return await service.check_limit(company_id, operation, quantity)
        
    except Exception as e:
        logger.error(f"Failed to check usage limit: {e}")
        return False, str(e), {}

