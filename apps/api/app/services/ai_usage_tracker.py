"""
AI Usage Tracking and Quota Enforcement Service.

Tracks per-LC, per-user, and per-tenant AI usage with rate limiting and quota enforcement.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from enum import Enum
from collections import defaultdict
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from ..models import User, Company, ValidationSession
from ..models.base import Base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

logger = logging.getLogger(__name__)


class AIFeature(str, Enum):
    """AI feature types for quota tracking."""
    LETTER = "letter"
    SUMMARY = "summary"
    TRANSLATION = "translation"
    CHAT = "chat"
    SYSTEM_ENRICHMENT = "system_enrichment"


class QuotaScope(str, Enum):
    """Quota scope levels."""
    PER_LC = "per_lc"
    PER_USER_DAY = "per_user_day"
    PER_TENANT_MONTH = "per_tenant_month"


class AIUsageRecord(Base):
    """Tracks AI usage for quota enforcement."""
    __tablename__ = "ai_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    validation_session_id = Column(UUID(as_uuid=True), ForeignKey('validation_sessions.id'), nullable=True, index=True)
    
    feature = Column(String(50), nullable=False)  # AIFeature enum
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Company")
    user = relationship("User")
    session = relationship("ValidationSession")


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, max_tokens: int, refill_rate: float, burst: int = 5):
        """
        Args:
            max_tokens: Maximum tokens in bucket
            refill_rate: Tokens per second
            burst: Additional burst capacity
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.burst = burst
        self.tokens = max_tokens
        self.last_refill = time.time()
    
    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if successful."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill tokens
        self.tokens = min(
            self.max_tokens + self.burst,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class AIUsageTracker:
    """Tracks and enforces AI usage quotas."""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Rate limiters: keyed by (scope, identifier)
        self._rate_limiters: Dict[Tuple[str, str], RateLimiter] = {}
        
        # Per-LC counters: keyed by validation_session_id
        self._per_lc_counters: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Load config from env
        self._load_config()
    
    def _load_config(self):
        """Load quota configuration from environment."""
        # SME per-LC limits
        self.sme_per_lc_limits = {
            AIFeature.LETTER: int(os.getenv("SME_PER_LC_LIMIT_LETTERS", "3")),
            AIFeature.SUMMARY: int(os.getenv("SME_PER_LC_LIMIT_SUMMARIES", "3")),
            AIFeature.TRANSLATION: int(os.getenv("SME_PER_LC_LIMIT_TRANSLATIONS", "5")),
            AIFeature.CHAT: int(os.getenv("SME_PER_LC_LIMIT_CHAT", "10")),
        }
        
        # Bank per-LC limits
        self.bank_per_lc_limits = {
            AIFeature.LETTER: int(os.getenv("BANK_PER_LC_LIMIT_LETTERS", "5")),
            AIFeature.SUMMARY: int(os.getenv("BANK_PER_LC_LIMIT_SUMMARIES", "5")),
            AIFeature.TRANSLATION: int(os.getenv("BANK_PER_LC_LIMIT_TRANSLATIONS", "10")),
            AIFeature.CHAT: int(os.getenv("BANK_PER_LC_LIMIT_CHAT", "20")),
        }
        
        # Bank tenant monthly pools
        self.bank_tenant_monthly = {
            AIFeature.LETTER: int(os.getenv("BANK_TENANT_MONTHLY_LETTERS", "1000")),
            AIFeature.TRANSLATION: int(os.getenv("BANK_TENANT_MONTHLY_TRANSLATIONS", "2000")),
            AIFeature.SUMMARY: int(os.getenv("BANK_TENANT_MONTHLY_SUMMARIES", "2000")),
            AIFeature.CHAT: int(os.getenv("BANK_TENANT_MONTHLY_CHAT", "5000")),
        }
        
        self.bank_reserve_percent = float(os.getenv("BANK_TENANT_RESERVE_PERCENT", "30"))
        
        # Rate limits
        self.rate_limit_per_user_per_min = int(os.getenv("AI_RATE_LIMIT_PER_USER_PER_MIN", "10"))
        self.rate_limit_per_tenant_per_min = int(os.getenv("AI_RATE_LIMIT_PER_TENANT_PER_MIN", "50"))
        self.min_interval_per_lc_ms = int(os.getenv("AI_MIN_INTERVAL_PER_LC_MS", "2000"))
    
    def _get_rate_limiter(self, scope: str, identifier: str) -> RateLimiter:
        """Get or create rate limiter for scope/identifier."""
        key = (scope, identifier)
        if key not in self._rate_limiters:
            if scope == "user":
                max_tokens = self.rate_limit_per_user_per_min
            elif scope == "tenant":
                max_tokens = self.rate_limit_per_tenant_per_min
            else:
                max_tokens = 10
            
            self._rate_limiters[key] = RateLimiter(
                max_tokens=max_tokens,
                refill_rate=max_tokens / 60.0,  # tokens per second
                burst=5
            )
        return self._rate_limiters[key]
    
    def check_quota(
        self,
        user: User,
        session: Optional[ValidationSession],
        feature: AIFeature,
        is_bank: bool = False
    ) -> Tuple[bool, Optional[str], Dict[str, int]]:
        """
        Check if quota allows the request.
        
        Returns:
            (allowed, error_message, remaining_quotas)
        """
        remaining = {}
        
        # 1. Per-LC quota check
        if session:
            session_id = str(session.id)
            per_lc_limits = self.bank_per_lc_limits if is_bank else self.sme_per_lc_limits
            current_count = self._per_lc_counters[session_id].get(feature.value, 0)
            limit = per_lc_limits.get(feature, 0)
            
            if current_count >= limit:
                return False, f"Per-LC limit reached: {limit} {feature.value} per validation session", {}
            
            remaining["per_lc"] = limit - current_count
        
        # 2. Per-user/day soft cap (banks only)
        if is_bank:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            user_day_count = self.db.query(func.count(AIUsageRecord.id)).filter(
                and_(
                    AIUsageRecord.user_id == user.id,
                    AIUsageRecord.created_at >= today_start,
                    AIUsageRecord.feature == feature.value
                )
            ).scalar() or 0
            
            soft_limit = 100
            burst_limit = 150
            
            # Check tenant remaining for burst
            tenant_remaining = self._get_tenant_monthly_remaining(user.company_id, feature)
            can_burst = tenant_remaining > 0.2  # >20% remaining
            
            if user_day_count >= (burst_limit if can_burst else soft_limit):
                return False, f"Daily user limit reached: {soft_limit} ops/day", {}
            
            remaining["per_user_day"] = (burst_limit if can_burst else soft_limit) - user_day_count
        
        # 3. Per-tenant/month pool (banks only)
        if is_bank:
            tenant_remaining = self._get_tenant_monthly_remaining(user.company_id, feature)
            if tenant_remaining <= 0:
                return False, "Tenant monthly quota exhausted", {}
            
            remaining["tenant_monthly"] = tenant_remaining
            
            # Budget protection: check reserve
            total_pool = self.bank_tenant_monthly.get(feature, 0)
            reserve_amount = int(total_pool * self.bank_reserve_percent / 100)
            
            if tenant_remaining < reserve_amount:
                # In reserve zone - apply restrictions
                if feature == AIFeature.CHAT:
                    return False, "Tenant quota in reserve zone - chat unavailable", {}
                # For other features, allow but with reduced output tokens
        
        # 4. Rate limiting
        user_limiter = self._get_rate_limiter("user", str(user.id))
        if not user_limiter.acquire():
            return False, "Rate limit exceeded: too many requests per minute", {}
        
        tenant_limiter = self._get_rate_limiter("tenant", str(user.company_id))
        if not tenant_limiter.acquire():
            return False, "Tenant rate limit exceeded", {}
        
        # 5. Per-LC interval guard
        if session:
            # Check last request time for this LC (simplified - in production use Redis)
            # For now, rely on rate limiter
            pass
        
        return True, None, remaining
    
    def get_quota_info(self, user: User, feature: AIFeature, is_bank: bool) -> Dict[str, Any]:
        """Get quota information for a user and feature."""
        is_bank = is_bank or user.role in ["bank_admin", "bank_officer"]
        
        # Get current usage
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        user_day_count = self.db.query(func.count(AIUsageRecord.id)).filter(
            and_(
                AIUsageRecord.user_id == user.id,
                AIUsageRecord.created_at >= today_start,
                AIUsageRecord.feature == feature.value
            )
        ).scalar() or 0
        
        # Get limits
        if is_bank:
            per_user_limit = 100
            tenant_limit = self.bank_tenant_monthly.get(feature, 1000)
            tenant_used = self.db.query(func.count(AIUsageRecord.id)).filter(
                and_(
                    AIUsageRecord.tenant_id == user.company_id,
                    AIUsageRecord.created_at >= month_start,
                    AIUsageRecord.feature == feature.value
                )
            ).scalar() or 0
            tenant_remaining = max(0, tenant_limit - tenant_used)
        else:
            per_user_limit = 50
            tenant_limit = 500
            tenant_used = 0
            tenant_remaining = tenant_limit
        
        # Calculate reset time (end of month for tenant, end of day for user)
        from datetime import timezone
        now = datetime.now(timezone.utc)
        next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        reset_at = next_month.isoformat()
        
        return {
            "used": user_day_count,
            "limit": per_user_limit,
            "remaining": max(0, per_user_limit - user_day_count),
            "tenant_used": tenant_used,
            "tenant_limit": tenant_limit,
            "tenant_remaining": tenant_remaining,
            "reset_at": reset_at
        }
    
    def _get_tenant_monthly_remaining(self, tenant_id: uuid.UUID, feature: AIFeature) -> int:
        """Get remaining monthly quota for tenant."""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        used = self.db.query(func.count(AIUsageRecord.id)).filter(
            and_(
                AIUsageRecord.tenant_id == tenant_id,
                AIUsageRecord.feature == feature.value,
                AIUsageRecord.created_at >= month_start
            )
        ).scalar() or 0
        
        total_pool = self.bank_tenant_monthly.get(feature, 0)
        return max(0, total_pool - used)
    
    def record_usage(
        self,
        user: User,
        session: Optional[ValidationSession],
        feature: AIFeature,
        tokens_in: int,
        tokens_out: int,
        estimated_cost: Optional[float] = None
    ):
        """Record AI usage for quota tracking."""
        # Increment per-LC counter
        if session:
            session_id = str(session.id)
            self._per_lc_counters[session_id][feature.value] += 1
        
        # Resolve tenant/company for usage record
        tenant_id = getattr(user, "company_id", None)
        if not tenant_id and session and getattr(session, "company_id", None):
            tenant_id = session.company_id
        if not tenant_id:
            logger.warning(
                "AI usage logging skipped: tenant_id missing (user_id=%s session_id=%s feature=%s)",
                getattr(user, "id", None),
                getattr(session, "id", None) if session else None,
                feature.value,
            )
            return
        
        # Create usage record
        record = AIUsageRecord(
            tenant_id=tenant_id,
            user_id=user.id,
            validation_session_id=session.id if session else None,
            feature=feature.value,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=str(estimated_cost) if estimated_cost else None
        )
        
        try:
            self.db.add(record)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to record AI usage (tenant_id=%s user_id=%s session_id=%s feature=%s): %s",
                tenant_id,
                getattr(user, "id", None),
                getattr(session, "id", None) if session else None,
                feature.value,
                e,
            )
    
    def get_usage_stats(
        self,
        user: User,
        session: Optional[ValidationSession] = None,
        is_bank: bool = False
    ) -> Dict[str, Any]:
        """Get current usage statistics."""
        stats = {}
        
        # Per-LC stats
        if session:
            session_id = str(session.id)
            per_lc_limits = self.bank_per_lc_limits if is_bank else self.sme_per_lc_limits
            stats["per_lc"] = {
                feature.value: {
                    "used": self._per_lc_counters[session_id].get(feature.value, 0),
                    "limit": per_lc_limits.get(feature, 0),
                    "remaining": per_lc_limits.get(feature, 0) - self._per_lc_counters[session_id].get(feature.value, 0)
                }
                for feature in [AIFeature.LETTER, AIFeature.SUMMARY, AIFeature.TRANSLATION, AIFeature.CHAT]
            }
        
        # Tenant monthly stats (banks only)
        if is_bank:
            stats["tenant_monthly"] = {
                feature.value: {
                    "used": self.bank_tenant_monthly.get(feature, 0) - self._get_tenant_monthly_remaining(user.company_id, feature),
                    "limit": self.bank_tenant_monthly.get(feature, 0),
                    "remaining": self._get_tenant_monthly_remaining(user.company_id, feature)
                }
                for feature in [AIFeature.LETTER, AIFeature.SUMMARY, AIFeature.TRANSLATION, AIFeature.CHAT]
            }
        
        return stats

