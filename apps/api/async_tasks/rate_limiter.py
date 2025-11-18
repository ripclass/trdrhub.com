#!/usr/bin/env python3
"""
LCopilot Trust Platform - Rate Limiter
Phase 4: Async Processing Pipeline

Implements tier-based rate limiting for async job processing.
"""

import time
import redis
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import json

class ConfigError(Exception):
    """Raised when configuration is invalid or missing"""
    pass

class RateLimiter:
    """Tier-based rate limiter for async processing jobs"""

    def __init__(self, config_path: str = "trust_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)

        # Validate Redis password is configured
        redis_password = os.environ.get('REDIS_PASSWORD')
        if not redis_password:
            raise ConfigError("REDIS_PASSWORD not found in environment variables. "
                            "Redis authentication is required for security")

        # Redis connection for distributed rate limiting with security
        redis_config = self.config.get('redis', {})
        self.redis_client = redis.Redis(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_password,
            ssl=redis_config.get('ssl', True),
            ssl_cert_reqs='required' if redis_config.get('ssl', True) else None,
            decode_responses=True
        )

        # Rate limit configuration
        self.rate_limits = self.config.get('async_processing', {}).get('rate_limits', {})

        # Default rate limits if not configured
        if not self.rate_limits:
            self.rate_limits = {
                'free': {
                    'jobs_per_hour': 10,
                    'jobs_per_day': 50,
                    'concurrent_jobs': 2
                },
                'pro': {
                    'jobs_per_hour': 100,
                    'jobs_per_day': 500,
                    'concurrent_jobs': 5
                },
                'enterprise': {
                    'jobs_per_hour': 1000,
                    'jobs_per_day': 10000,
                    'concurrent_jobs': 20
                }
            }

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load trust platform configuration"""
        import yaml

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found, using defaults")
            return {}

    def check_rate_limit(self, user_id: str, tier: str) -> bool:
        """
        Check if user can submit a new job based on tier limits

        Args:
            user_id: User identifier
            tier: User tier (free, pro, enterprise)

        Returns:
            bool: True if user can submit job, False if rate limited
        """
        try:
            tier_limits = self.rate_limits.get(tier, self.rate_limits['free'])

            # Check hourly limit
            if not self._check_hourly_limit(user_id, tier_limits['jobs_per_hour']):
                self.logger.warning(f"User {user_id} exceeded hourly limit for tier {tier}")
                return False

            # Check daily limit
            if not self._check_daily_limit(user_id, tier_limits['jobs_per_day']):
                self.logger.warning(f"User {user_id} exceeded daily limit for tier {tier}")
                return False

            # Check concurrent job limit
            if not self._check_concurrent_limit(user_id, tier_limits['concurrent_jobs']):
                self.logger.warning(f"User {user_id} exceeded concurrent job limit for tier {tier}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Rate limit check failed for user {user_id}: {e}")
            # Fail open - allow the request if rate limiting fails
            return True

    def _check_hourly_limit(self, user_id: str, limit: int) -> bool:
        """Check hourly rate limit"""
        hour_key = f"rate_limit:hourly:{user_id}:{self._get_current_hour()}"

        try:
            current_count = int(self.redis_client.get(hour_key) or 0)
            return current_count < limit
        except Exception as e:
            self.logger.error(f"Failed to check hourly limit: {e}")
            return True

    def _check_daily_limit(self, user_id: str, limit: int) -> bool:
        """Check daily rate limit"""
        day_key = f"rate_limit:daily:{user_id}:{self._get_current_day()}"

        try:
            current_count = int(self.redis_client.get(day_key) or 0)
            return current_count < limit
        except Exception as e:
            self.logger.error(f"Failed to check daily limit: {e}")
            return True

    def _check_concurrent_limit(self, user_id: str, limit: int) -> bool:
        """Check concurrent job limit"""
        concurrent_key = f"rate_limit:concurrent:{user_id}"

        try:
            # Get list of active jobs for user
            active_jobs = self.redis_client.smembers(concurrent_key)

            # Clean up expired jobs (older than 1 hour)
            current_time = time.time()
            for job_data in list(active_jobs):
                try:
                    job_info = json.loads(job_data)
                    if current_time - job_info['start_time'] > 3600:  # 1 hour timeout
                        self.redis_client.srem(concurrent_key, job_data)
                except:
                    # Remove malformed entries
                    self.redis_client.srem(concurrent_key, job_data)

            # Get updated count
            current_count = self.redis_client.scard(concurrent_key)
            return current_count < limit

        except Exception as e:
            self.logger.error(f"Failed to check concurrent limit: {e}")
            return True

    def record_request(self, user_id: str, tier: str, job_id: Optional[str] = None):
        """
        Record a successful job submission

        Args:
            user_id: User identifier
            tier: User tier
            job_id: Optional job ID for concurrent tracking
        """
        try:
            # Increment hourly counter
            hour_key = f"rate_limit:hourly:{user_id}:{self._get_current_hour()}"
            pipe = self.redis_client.pipeline()
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)  # Expire in 1 hour

            # Increment daily counter
            day_key = f"rate_limit:daily:{user_id}:{self._get_current_day()}"
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)  # Expire in 24 hours

            # Add to concurrent jobs if job_id provided
            if job_id:
                concurrent_key = f"rate_limit:concurrent:{user_id}"
                job_data = json.dumps({
                    'job_id': job_id,
                    'start_time': time.time(),
                    'tier': tier
                })
                pipe.sadd(concurrent_key, job_data)
                pipe.expire(concurrent_key, 3600)  # Expire in 1 hour

            pipe.execute()

            self.logger.debug(f"Recorded request for user {user_id} (tier: {tier})")

        except Exception as e:
            self.logger.error(f"Failed to record request for user {user_id}: {e}")

    def remove_concurrent_job(self, user_id: str, job_id: str):
        """
        Remove job from concurrent tracking when it completes

        Args:
            user_id: User identifier
            job_id: Job identifier
        """
        try:
            concurrent_key = f"rate_limit:concurrent:{user_id}"
            active_jobs = self.redis_client.smembers(concurrent_key)

            # Find and remove the specific job
            for job_data in active_jobs:
                try:
                    job_info = json.loads(job_data)
                    if job_info['job_id'] == job_id:
                        self.redis_client.srem(concurrent_key, job_data)
                        break
                except:
                    continue

            self.logger.debug(f"Removed concurrent job {job_id} for user {user_id}")

        except Exception as e:
            self.logger.error(f"Failed to remove concurrent job {job_id}: {e}")

    def get_user_limits(self, user_id: str, tier: str) -> Dict[str, Any]:
        """
        Get current usage and limits for a user

        Args:
            user_id: User identifier
            tier: User tier

        Returns:
            Dict with current usage and limits
        """
        try:
            tier_limits = self.rate_limits.get(tier, self.rate_limits['free'])

            # Get current usage
            hour_key = f"rate_limit:hourly:{user_id}:{self._get_current_hour()}"
            day_key = f"rate_limit:daily:{user_id}:{self._get_current_day()}"
            concurrent_key = f"rate_limit:concurrent:{user_id}"

            hourly_count = int(self.redis_client.get(hour_key) or 0)
            daily_count = int(self.redis_client.get(day_key) or 0)
            concurrent_count = self.redis_client.scard(concurrent_key)

            return {
                'tier': tier,
                'limits': tier_limits,
                'usage': {
                    'jobs_this_hour': hourly_count,
                    'jobs_today': daily_count,
                    'concurrent_jobs': concurrent_count
                },
                'remaining': {
                    'hourly': max(0, tier_limits['jobs_per_hour'] - hourly_count),
                    'daily': max(0, tier_limits['jobs_per_day'] - daily_count),
                    'concurrent': max(0, tier_limits['concurrent_jobs'] - concurrent_count)
                },
                'reset_times': {
                    'hourly': self._get_next_hour(),
                    'daily': self._get_next_day()
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to get user limits for {user_id}: {e}")
            return {'error': str(e)}

    def _get_current_hour(self) -> str:
        """Get current hour key for rate limiting"""
        return datetime.utcnow().strftime('%Y%m%d_%H')

    def _get_current_day(self) -> str:
        """Get current day key for rate limiting"""
        return datetime.utcnow().strftime('%Y%m%d')

    def _get_next_hour(self) -> str:
        """Get timestamp for next hour reset"""
        next_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour.isoformat()

    def _get_next_day(self) -> str:
        """Get timestamp for next day reset"""
        next_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return next_day.isoformat()

    def reset_user_limits(self, user_id: str) -> bool:
        """
        Reset all rate limits for a user (admin function)

        Args:
            user_id: User identifier

        Returns:
            bool: True if reset successful
        """
        try:
            # Find all rate limit keys for user
            pattern = f"rate_limit:*:{user_id}:*"
            keys = self.redis_client.keys(pattern)

            # Also reset concurrent jobs
            concurrent_key = f"rate_limit:concurrent:{user_id}"
            keys.append(concurrent_key)

            if keys:
                self.redis_client.delete(*keys)

            self.logger.info(f"Reset rate limits for user {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to reset limits for user {user_id}: {e}")
            return False

    def get_all_user_stats(self) -> Dict[str, Any]:
        """Get rate limiting stats for all users"""
        try:
            stats = {}

            # Get all hourly keys
            hour_pattern = f"rate_limit:hourly:*:{self._get_current_hour()}"
            hourly_keys = self.redis_client.keys(hour_pattern)

            for key in hourly_keys:
                # Extract user_id from key
                parts = key.split(':')
                if len(parts) >= 4:
                    user_id = parts[2]
                    count = int(self.redis_client.get(key) or 0)

                    if user_id not in stats:
                        stats[user_id] = {}

                    stats[user_id]['hourly_requests'] = count

            # Get all daily keys
            day_pattern = f"rate_limit:daily:*:{self._get_current_day()}"
            daily_keys = self.redis_client.keys(day_pattern)

            for key in daily_keys:
                # Extract user_id from key
                parts = key.split(':')
                if len(parts) >= 4:
                    user_id = parts[2]
                    count = int(self.redis_client.get(key) or 0)

                    if user_id not in stats:
                        stats[user_id] = {}

                    stats[user_id]['daily_requests'] = count

            # Get concurrent job counts
            concurrent_pattern = "rate_limit:concurrent:*"
            concurrent_keys = self.redis_client.keys(concurrent_pattern)

            for key in concurrent_keys:
                # Extract user_id from key
                parts = key.split(':')
                if len(parts) >= 3:
                    user_id = parts[2]
                    count = self.redis_client.scard(key)

                    if user_id not in stats:
                        stats[user_id] = {}

                    stats[user_id]['concurrent_jobs'] = count

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get all user stats: {e}")
            return {'error': str(e)}