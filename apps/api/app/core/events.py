"""
Event system for notifications and event-driven workflows.

This module provides event classes and filters for the notification system.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event type enumeration"""
    LC_CREATED = "lc.created"
    LC_UPDATED = "lc.updated"
    LC_VALIDATED = "lc.validated"
    DISCREPANCY_FOUND = "discrepancy.found"
    DISCREPANCY_RESOLVED = "discrepancy.resolved"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    USER_INVITED = "user.invited"
    USER_ACTIVATED = "user.activated"
    # Add more event types as needed


class EventSeverity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BaseEvent(BaseModel):
    """Base event class for all system events"""
    
    event_type: EventType
    tenant_alias: str
    bank_alias: Optional[str] = None
    severity: EventSeverity = EventSeverity.INFO
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class EventFilter(BaseModel):
    """Filter for matching events to subscriptions"""
    
    event_types: Optional[list[str]] = None
    severities: Optional[list[str]] = None
    tenant_aliases: Optional[list[str]] = None
    bank_aliases: Optional[list[str]] = None
    
    def matches(self, event: BaseEvent) -> bool:
        """Check if event matches this filter"""
        # If no filters specified, match all
        if not any([self.event_types, self.severities, self.tenant_aliases, self.bank_aliases]):
            return True
        
        # Check event type
        if self.event_types and event.event_type.value not in self.event_types:
            return False
        
        # Check severity
        if self.severities and event.severity.value not in self.severities:
            return False
        
        # Check tenant
        if self.tenant_aliases and event.tenant_alias not in self.tenant_aliases:
            return False
        
        # Check bank
        if self.bank_aliases:
            if not event.bank_alias or event.bank_alias not in self.bank_aliases:
                return False
        
        return True

