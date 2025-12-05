"""
Tracking Models - Container & Vessel Tracking System

This module defines:
- TrackingType: Enum for tracking types (container, vessel)
- ShipmentStatus: Enum for shipment status
- AlertType: Enum for alert types
- NotificationStatus: Enum for notification status
- TrackedShipment: User's shipment portfolio
- TrackingAlert: Alert configurations
- TrackingEvent: Historical tracking events
- TrackingNotification: Sent notification log
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Boolean, Integer, Float,
    CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ============== Enums ==============

class TrackingType(str, Enum):
    """Type of tracking"""
    CONTAINER = "container"
    VESSEL = "vessel"


class ShipmentStatus(str, Enum):
    """Status of a tracked shipment"""
    BOOKED = "booked"
    GATE_IN = "gate_in"
    LOADED = "loaded"
    DEPARTED = "departed"
    IN_TRANSIT = "in_transit"
    TRANSSHIPMENT = "transshipment"
    AT_PORT = "at_port"
    ARRIVED = "arrived"
    DISCHARGED = "discharged"
    GATE_OUT = "gate_out"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    EXCEPTION = "exception"
    UNKNOWN = "unknown"


class AlertType(str, Enum):
    """Types of tracking alerts"""
    ARRIVAL = "arrival"           # Alert when shipment arrives
    DEPARTURE = "departure"       # Alert when shipment departs
    DELAY = "delay"               # Alert when delay detected
    ETA_CHANGE = "eta_change"     # Alert when ETA changes
    STATUS_CHANGE = "status_change"  # Alert on any status change
    LC_RISK = "lc_risk"           # Alert when ETA approaches LC expiry
    EXCEPTION = "exception"       # Alert on exceptions


class NotificationStatus(str, Enum):
    """Status of sent notifications"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


# ============== Models ==============

class TrackedShipment(Base):
    """
    User's tracked shipment portfolio.
    
    Stores shipments that users want to monitor, including
    container and vessel tracking with optional LC linkage.
    """
    __tablename__ = "tracked_shipments"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Ownership
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    
    # Shipment identification
    reference = Column(String(50), nullable=False)  # Container number or vessel IMO
    tracking_type = Column(String(20), nullable=False, default=TrackingType.CONTAINER.value)
    nickname = Column(String(100), nullable=True)   # User-friendly name
    
    # Carrier info
    carrier = Column(String(100), nullable=True)
    carrier_code = Column(String(10), nullable=True)
    
    # Route
    origin_port = Column(String(200), nullable=True)
    origin_code = Column(String(10), nullable=True)
    origin_country = Column(String(100), nullable=True)
    destination_port = Column(String(200), nullable=True)
    destination_code = Column(String(10), nullable=True)
    destination_country = Column(String(100), nullable=True)
    
    # Current status
    status = Column(String(50), nullable=True, default=ShipmentStatus.UNKNOWN.value)
    current_location = Column(String(300), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    progress = Column(Integer, default=0)  # 0-100 percentage
    
    # Timing
    etd = Column(DateTime(timezone=True), nullable=True)  # Estimated time of departure
    eta = Column(DateTime(timezone=True), nullable=True)  # Estimated time of arrival
    eta_confidence = Column(Integer, nullable=True)       # 0-100 confidence score
    ata = Column(DateTime(timezone=True), nullable=True)  # Actual time of arrival
    
    # Vessel info (for container tracking)
    vessel_name = Column(String(200), nullable=True)
    vessel_imo = Column(String(20), nullable=True)
    vessel_mmsi = Column(String(20), nullable=True)
    voyage = Column(String(50), nullable=True)
    vessel_flag = Column(String(50), nullable=True)
    
    # LC linkage
    lc_number = Column(String(100), nullable=True)
    lc_expiry = Column(DateTime(timezone=True), nullable=True)
    bl_number = Column(String(100), nullable=True)
    booking_number = Column(String(100), nullable=True)
    
    # Trade details
    shipper = Column(String(200), nullable=True)
    consignee = Column(String(200), nullable=True)
    goods_description = Column(Text, nullable=True)
    
    # User notes
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    
    # Tracking metadata
    is_active = Column(Boolean, default=True, nullable=False)
    last_checked = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), nullable=True)
    data_source = Column(String(50), nullable=True)  # searates, portcast, mock, etc.
    raw_data = Column(JSONB, nullable=True)  # Store full API response
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    alerts = relationship("TrackingAlert", back_populates="shipment", cascade="all, delete-orphan")
    events = relationship("TrackingEvent", back_populates="shipment", cascade="all, delete-orphan", order_by="TrackingEvent.event_time.desc()")
    
    # Indexes
    __table_args__ = (
        Index("ix_tracked_shipments_user_reference", "user_id", "reference"),
        Index("ix_tracked_shipments_user_active", "user_id", "is_active"),
        UniqueConstraint("user_id", "reference", "tracking_type", name="uq_user_shipment"),
    )
    
    def __repr__(self):
        return f"<TrackedShipment {self.reference} ({self.tracking_type})>"


class TrackingAlert(Base):
    """
    Alert configurations for tracked shipments.
    
    Users can set up alerts for various events like arrival,
    delays, ETA changes, etc.
    """
    __tablename__ = "tracking_alerts"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Ownership
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shipment_id = Column(PGUUID(as_uuid=True), ForeignKey("tracked_shipments.id", ondelete="CASCADE"), nullable=True)
    
    # Alert target (can exist without shipment for ad-hoc alerts)
    reference = Column(String(50), nullable=False)
    tracking_type = Column(String(20), nullable=False, default=TrackingType.CONTAINER.value)
    
    # Alert configuration
    alert_type = Column(String(50), nullable=False, default=AlertType.ARRIVAL.value)
    threshold_hours = Column(Integer, nullable=True)  # For delay alerts: trigger if delay > X hours
    threshold_days = Column(Integer, nullable=True)   # For LC risk: alert if ETA within X days of LC expiry
    
    # Notification preferences
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_sms = Column(Boolean, default=False, nullable=False)
    email_address = Column(String(255), nullable=True)  # Override user's default email
    phone_number = Column(String(20), nullable=True)
    
    # Additional recipients (JSON array of emails)
    additional_recipients = Column(JSONB, nullable=True, default=list)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    shipment = relationship("TrackedShipment", back_populates="alerts")
    notifications = relationship("TrackingNotification", back_populates="alert", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("ix_tracking_alerts_user_active", "user_id", "is_active"),
        Index("ix_tracking_alerts_reference", "reference"),
    )
    
    def __repr__(self):
        return f"<TrackingAlert {self.alert_type} for {self.reference}>"


class TrackingEvent(Base):
    """
    Historical tracking events for a shipment.
    
    Stores the timeline of events (gate in, loaded, departed, etc.)
    for audit trail and historical analysis.
    """
    __tablename__ = "tracking_events"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Parent shipment
    shipment_id = Column(PGUUID(as_uuid=True), ForeignKey("tracked_shipments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(300), nullable=True)
    location_code = Column(String(10), nullable=True)
    description = Column(Text, nullable=True)
    
    # Position (optional)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Vessel info at time of event
    vessel_name = Column(String(200), nullable=True)
    voyage = Column(String(50), nullable=True)
    
    # Status classification
    status = Column(String(50), nullable=True)  # completed, current, upcoming
    is_actual = Column(Boolean, default=True)   # True for actual events, False for estimates
    
    # Source tracking
    data_source = Column(String(50), nullable=True)
    external_id = Column(String(100), nullable=True)  # ID from source system
    raw_data = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    shipment = relationship("TrackedShipment", back_populates="events")
    
    # Indexes
    __table_args__ = (
        Index("ix_tracking_events_shipment_time", "shipment_id", "event_time"),
    )
    
    def __repr__(self):
        return f"<TrackingEvent {self.event_type} at {self.location}>"


class TrackingNotification(Base):
    """
    Log of sent notifications.
    
    Tracks all notifications sent for alerts, including
    delivery status and any error messages.
    """
    __tablename__ = "tracking_notifications"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Parent alert
    alert_id = Column(PGUUID(as_uuid=True), ForeignKey("tracking_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Notification details
    notification_type = Column(String(20), nullable=False)  # email, sms
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    
    # Trigger context
    trigger_reason = Column(String(200), nullable=True)  # e.g., "ETA within 24 hours"
    shipment_reference = Column(String(50), nullable=True)
    shipment_status = Column(String(50), nullable=True)
    
    # Delivery status
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING.value)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # External IDs for tracking
    external_id = Column(String(100), nullable=True)  # Resend/Twilio message ID
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    alert = relationship("TrackingAlert", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index("ix_tracking_notifications_alert", "alert_id"),
        Index("ix_tracking_notifications_status", "status"),
    )
    
    def __repr__(self):
        return f"<TrackingNotification {self.notification_type} to {self.recipient}>"


# ============== Export ==============

__all__ = [
    "TrackingType",
    "ShipmentStatus",
    "AlertType",
    "NotificationStatus",
    "TrackedShipment",
    "TrackingAlert",
    "TrackingEvent",
    "TrackingNotification",
]

