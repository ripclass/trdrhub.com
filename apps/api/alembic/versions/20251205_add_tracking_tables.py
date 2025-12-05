"""Add tracking tables for Container & Vessel Tracker

Revision ID: tracking_tables_001
Revises: billing_localization_001
Create Date: 2025-12-05

This migration creates:
- tracked_shipments: User's shipment portfolio
- tracking_alerts: Alert configurations
- tracking_events: Historical tracking events
- tracking_notifications: Sent notification log
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = 'tracking_tables_001'
down_revision = 'billing_localization_001'
branch_labels = None
depends_on = None


def upgrade():
    # ============== tracked_shipments ==============
    op.create_table(
        'tracked_shipments',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Ownership
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_id', UUID(as_uuid=True), sa.ForeignKey('companies.id', ondelete='SET NULL'), nullable=True),
        
        # Shipment identification
        sa.Column('reference', sa.String(50), nullable=False),
        sa.Column('tracking_type', sa.String(20), nullable=False, server_default='container'),
        sa.Column('nickname', sa.String(100), nullable=True),
        
        # Carrier info
        sa.Column('carrier', sa.String(100), nullable=True),
        sa.Column('carrier_code', sa.String(10), nullable=True),
        
        # Route
        sa.Column('origin_port', sa.String(200), nullable=True),
        sa.Column('origin_code', sa.String(10), nullable=True),
        sa.Column('origin_country', sa.String(100), nullable=True),
        sa.Column('destination_port', sa.String(200), nullable=True),
        sa.Column('destination_code', sa.String(10), nullable=True),
        sa.Column('destination_country', sa.String(100), nullable=True),
        
        # Current status
        sa.Column('status', sa.String(50), nullable=True, server_default='unknown'),
        sa.Column('current_location', sa.String(300), nullable=True),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('progress', sa.Integer, server_default='0'),
        
        # Timing
        sa.Column('etd', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eta', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eta_confidence', sa.Integer, nullable=True),
        sa.Column('ata', sa.DateTime(timezone=True), nullable=True),
        
        # Vessel info
        sa.Column('vessel_name', sa.String(200), nullable=True),
        sa.Column('vessel_imo', sa.String(20), nullable=True),
        sa.Column('vessel_mmsi', sa.String(20), nullable=True),
        sa.Column('voyage', sa.String(50), nullable=True),
        sa.Column('vessel_flag', sa.String(50), nullable=True),
        
        # LC linkage
        sa.Column('lc_number', sa.String(100), nullable=True),
        sa.Column('lc_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bl_number', sa.String(100), nullable=True),
        sa.Column('booking_number', sa.String(100), nullable=True),
        
        # Trade details
        sa.Column('shipper', sa.String(200), nullable=True),
        sa.Column('consignee', sa.String(200), nullable=True),
        sa.Column('goods_description', sa.Text, nullable=True),
        
        # User notes
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('tags', JSONB, nullable=True, server_default='[]'),
        
        # Tracking metadata
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('last_checked', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_source', sa.String(50), nullable=True),
        sa.Column('raw_data', JSONB, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        
        # Constraints
        sa.CheckConstraint("tracking_type IN ('container', 'vessel')", name='valid_tracking_type'),
        sa.UniqueConstraint('user_id', 'reference', 'tracking_type', name='uq_user_shipment'),
    )
    
    # Indexes for tracked_shipments
    op.create_index('ix_tracked_shipments_user_id', 'tracked_shipments', ['user_id'])
    op.create_index('ix_tracked_shipments_user_reference', 'tracked_shipments', ['user_id', 'reference'])
    op.create_index('ix_tracked_shipments_user_active', 'tracked_shipments', ['user_id', 'is_active'])
    op.create_index('ix_tracked_shipments_status', 'tracked_shipments', ['status'])
    op.create_index('ix_tracked_shipments_eta', 'tracked_shipments', ['eta'])
    
    # ============== tracking_alerts ==============
    op.create_table(
        'tracking_alerts',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Ownership
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('shipment_id', UUID(as_uuid=True), sa.ForeignKey('tracked_shipments.id', ondelete='CASCADE'), nullable=True),
        
        # Alert target
        sa.Column('reference', sa.String(50), nullable=False),
        sa.Column('tracking_type', sa.String(20), nullable=False, server_default='container'),
        
        # Alert configuration
        sa.Column('alert_type', sa.String(50), nullable=False, server_default='arrival'),
        sa.Column('threshold_hours', sa.Integer, nullable=True),
        sa.Column('threshold_days', sa.Integer, nullable=True),
        
        # Notification preferences
        sa.Column('notify_email', sa.Boolean, server_default='true', nullable=False),
        sa.Column('notify_sms', sa.Boolean, server_default='false', nullable=False),
        sa.Column('email_address', sa.String(255), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('additional_recipients', JSONB, nullable=True, server_default='[]'),
        
        # Status
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer, server_default='0', nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        
        # Constraints
        sa.CheckConstraint("alert_type IN ('arrival', 'departure', 'delay', 'eta_change', 'status_change', 'lc_risk', 'exception')", name='valid_alert_type'),
    )
    
    # Indexes for tracking_alerts
    op.create_index('ix_tracking_alerts_user_id', 'tracking_alerts', ['user_id'])
    op.create_index('ix_tracking_alerts_user_active', 'tracking_alerts', ['user_id', 'is_active'])
    op.create_index('ix_tracking_alerts_reference', 'tracking_alerts', ['reference'])
    op.create_index('ix_tracking_alerts_shipment_id', 'tracking_alerts', ['shipment_id'])
    
    # ============== tracking_events ==============
    op.create_table(
        'tracking_events',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Parent shipment
        sa.Column('shipment_id', UUID(as_uuid=True), sa.ForeignKey('tracked_shipments.id', ondelete='CASCADE'), nullable=False),
        
        # Event details
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(300), nullable=True),
        sa.Column('location_code', sa.String(10), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        
        # Position
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        
        # Vessel info at time of event
        sa.Column('vessel_name', sa.String(200), nullable=True),
        sa.Column('voyage', sa.String(50), nullable=True),
        
        # Status classification
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('is_actual', sa.Boolean, server_default='true'),
        
        # Source tracking
        sa.Column('data_source', sa.String(50), nullable=True),
        sa.Column('external_id', sa.String(100), nullable=True),
        sa.Column('raw_data', JSONB, nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Indexes for tracking_events
    op.create_index('ix_tracking_events_shipment_id', 'tracking_events', ['shipment_id'])
    op.create_index('ix_tracking_events_shipment_time', 'tracking_events', ['shipment_id', 'event_time'])
    op.create_index('ix_tracking_events_event_type', 'tracking_events', ['event_type'])
    
    # ============== tracking_notifications ==============
    op.create_table(
        'tracking_notifications',
        # Primary key
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        
        # Parent alert
        sa.Column('alert_id', UUID(as_uuid=True), sa.ForeignKey('tracking_alerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        
        # Notification details
        sa.Column('notification_type', sa.String(20), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text, nullable=True),
        
        # Trigger context
        sa.Column('trigger_reason', sa.String(200), nullable=True),
        sa.Column('shipment_reference', sa.String(50), nullable=True),
        sa.Column('shipment_status', sa.String(50), nullable=True),
        
        # Delivery status
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        
        # External IDs
        sa.Column('external_id', sa.String(100), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # Constraints
        sa.CheckConstraint("notification_type IN ('email', 'sms')", name='valid_notification_type'),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed', 'bounced')", name='valid_notification_status'),
    )
    
    # Indexes for tracking_notifications
    op.create_index('ix_tracking_notifications_alert_id', 'tracking_notifications', ['alert_id'])
    op.create_index('ix_tracking_notifications_user_id', 'tracking_notifications', ['user_id'])
    op.create_index('ix_tracking_notifications_status', 'tracking_notifications', ['status'])


def downgrade():
    # Drop tracking_notifications
    op.drop_index('ix_tracking_notifications_status', 'tracking_notifications')
    op.drop_index('ix_tracking_notifications_user_id', 'tracking_notifications')
    op.drop_index('ix_tracking_notifications_alert_id', 'tracking_notifications')
    op.drop_table('tracking_notifications')
    
    # Drop tracking_events
    op.drop_index('ix_tracking_events_event_type', 'tracking_events')
    op.drop_index('ix_tracking_events_shipment_time', 'tracking_events')
    op.drop_index('ix_tracking_events_shipment_id', 'tracking_events')
    op.drop_table('tracking_events')
    
    # Drop tracking_alerts
    op.drop_index('ix_tracking_alerts_shipment_id', 'tracking_alerts')
    op.drop_index('ix_tracking_alerts_reference', 'tracking_alerts')
    op.drop_index('ix_tracking_alerts_user_active', 'tracking_alerts')
    op.drop_index('ix_tracking_alerts_user_id', 'tracking_alerts')
    op.drop_table('tracking_alerts')
    
    # Drop tracked_shipments
    op.drop_index('ix_tracked_shipments_eta', 'tracked_shipments')
    op.drop_index('ix_tracked_shipments_status', 'tracked_shipments')
    op.drop_index('ix_tracked_shipments_user_active', 'tracked_shipments')
    op.drop_index('ix_tracked_shipments_user_reference', 'tracked_shipments')
    op.drop_index('ix_tracked_shipments_user_id', 'tracked_shipments')
    op.drop_table('tracked_shipments')

