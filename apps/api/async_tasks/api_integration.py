#!/usr/bin/env python3
"""
LCopilot Trust Platform - API Integration for Async Processing
Phase 4: Async Processing Pipeline

Flask routes and integration for async document processing.
"""

from flask import Blueprint, request, jsonify, current_app
import json
import os
import tempfile
import uuid
from typing import Dict, Any, Optional
import logging
from werkzeug.utils import secure_filename

from .queue_producer import QueueProducer, QueueError, RateLimitExceeded
from .job_status import JobStatusManager
from .rate_limiter import RateLimiter

# Create Blueprint for async processing routes
async_bp = Blueprint('async', __name__, url_prefix='/api/async')

logger = logging.getLogger(__name__)

# Initialize components (will be configured in app startup)
queue_producer = None
job_status_manager = None
rate_limiter = None

def init_async_components(app):
    """Initialize async processing components"""
    global queue_producer, job_status_manager, rate_limiter

    config_path = app.config.get('TRUST_CONFIG_PATH', 'trust_config.yaml')

    queue_producer = QueueProducer(config_path)
    job_status_manager = JobStatusManager(config_path)
    rate_limiter = RateLimiter(config_path)

    logger.info("Async processing components initialized")

@async_bp.route('/submit', methods=['POST'])
def submit_async_job():
    """
    Submit document for async processing

    Expected request:
    {
        "user_id": "user123",
        "tier": "pro",
        "lc_document": { ... },
        "bank_mode": "BRAC_BANK",  // optional
        "options": { ... }  // optional
    }

    Plus file upload or document_url
    """
    try:
        # Parse request data
        user_id = request.form.get('user_id') or request.json.get('user_id')
        tier = request.form.get('tier') or request.json.get('tier', 'free')
        bank_mode = request.form.get('bank_mode') or request.json.get('bank_mode')

        # Parse LC document
        lc_document_str = request.form.get('lc_document') or request.json.get('lc_document')
        if isinstance(lc_document_str, str):
            lc_document = json.loads(lc_document_str)
        else:
            lc_document = lc_document_str

        # Parse options
        options_str = request.form.get('options') or request.json.get('options', '{}')
        if isinstance(options_str, str):
            options = json.loads(options_str)
        else:
            options = options_str

        # Validate required fields
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        if not lc_document:
            return jsonify({'error': 'lc_document is required'}), 400

        # Handle document upload
        document_path = None

        if 'document' in request.files:
            # File upload
            file = request.files['document']
            if file and file.filename:
                # Save to temporary location
                filename = secure_filename(file.filename)
                temp_dir = tempfile.mkdtemp()
                document_path = os.path.join(temp_dir, filename)
                file.save(document_path)

        elif request.json and request.json.get('document_url'):
            # URL-based document (would need to download)
            document_url = request.json['document_url']
            document_path = _download_document_from_url(document_url)

        else:
            return jsonify({'error': 'Document file or URL is required'}), 400

        # Check rate limits before processing
        if not rate_limiter.check_rate_limit(user_id, tier):
            user_limits = rate_limiter.get_user_limits(user_id, tier)
            return jsonify({
                'error': 'Rate limit exceeded',
                'limits': user_limits,
                'retry_after': user_limits.get('reset_times', {}).get('hourly')
            }), 429

        # Submit job to queue
        job_id = queue_producer.enqueue_job(
            user_id=user_id,
            tier=tier,
            document_path=document_path,
            lc_document=lc_document,
            bank_mode=bank_mode,
            options=options
        )

        # Return job ID and status endpoint
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status_url': f'/api/async/status/{job_id}',
            'estimated_processing_time': _estimate_processing_time(tier, lc_document),
            'message': 'Document submitted for processing'
        }), 202

    except RateLimitExceeded as e:
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': str(e)
        }), 429

    except QueueError as e:
        logger.error(f"Queue error: {e}")
        return jsonify({
            'error': 'Failed to queue job',
            'message': str(e)
        }), 500

    except Exception as e:
        logger.error(f"Async job submission failed: {e}")
        return jsonify({
            'error': 'Job submission failed',
            'message': str(e)
        }), 500

@async_bp.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """Get status of async job"""
    try:
        job_data = job_status_manager.get_job_status(job_id)

        if not job_data:
            return jsonify({'error': 'Job not found'}), 404

        # Filter sensitive data for API response
        response_data = {
            'job_id': job_data['job_id'],
            'status': job_data['status'],
            'progress': job_data.get('progress', 0),
            'message': job_data.get('message', ''),
            'created_at': job_data['created_at'],
            'updated_at': job_data['updated_at'],
            'tier': job_data.get('tier'),
            'processing_time': job_data.get('processing_time')
        }

        # Include results if completed
        if job_data.get('status') == 'completed':
            response_data['results'] = job_data.get('results')

        # Include error if failed
        if job_data.get('status') == 'failed':
            response_data['error'] = job_data.get('error')

        # Include recent updates
        updates = job_data.get('updates', [])
        if updates:
            response_data['recent_updates'] = updates[-5:]  # Last 5 updates

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        return jsonify({
            'error': 'Failed to get job status',
            'message': str(e)
        }), 500

@async_bp.route('/status/<job_id>/poll', methods=['GET'])
def poll_job_status(job_id: str):
    """Poll job status until completion"""
    try:
        timeout = min(int(request.args.get('timeout', 300)), 300)  # Max 5 minutes
        poll_interval = int(request.args.get('interval', 2000))  # Default 2 seconds

        job_data = job_status_manager.poll_job_status(
            job_id,
            timeout_seconds=timeout,
            poll_interval_ms=poll_interval
        )

        if 'error' in job_data:
            return jsonify(job_data), 404

        # Filter response data
        response_data = {
            'job_id': job_data['job_id'],
            'status': job_data['status'],
            'progress': job_data.get('progress', 0),
            'message': job_data.get('message', ''),
            'processing_time': job_data.get('processing_time'),
            'completed_at': job_data.get('completed_at'),
            'failed_at': job_data.get('failed_at')
        }

        # Include results if completed
        if job_data.get('status') == 'completed':
            response_data['results'] = job_data.get('results')

        # Include error if failed
        if job_data.get('status') == 'failed':
            response_data['error'] = job_data.get('error')

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Failed to poll job status {job_id}: {e}")
        return jsonify({
            'error': 'Failed to poll job status',
            'message': str(e)
        }), 500

@async_bp.route('/jobs/<user_id>', methods=['GET'])
def get_user_jobs(user_id: str):
    """Get jobs for a specific user"""
    try:
        limit = int(request.args.get('limit', 50))
        status_filter = request.args.get('status')

        jobs = job_status_manager.get_user_jobs(
            user_id,
            limit=limit,
            status_filter=status_filter
        )

        return jsonify({
            'user_id': user_id,
            'jobs': jobs,
            'count': len(jobs)
        })

    except Exception as e:
        logger.error(f"Failed to get user jobs for {user_id}: {e}")
        return jsonify({
            'error': 'Failed to get user jobs',
            'message': str(e)
        }), 500

@async_bp.route('/jobs/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id: str):
    """Cancel a job"""
    try:
        reason = request.json.get('reason', 'User cancelled') if request.json else 'User cancelled'

        success = job_status_manager.cancel_job(job_id, reason)

        if success:
            return jsonify({
                'success': True,
                'message': f'Job {job_id} cancelled'
            })
        else:
            return jsonify({
                'error': 'Failed to cancel job',
                'message': 'Job may not exist or cannot be cancelled in current state'
            }), 400

    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return jsonify({
            'error': 'Failed to cancel job',
            'message': str(e)
        }), 500

@async_bp.route('/limits/<user_id>', methods=['GET'])
def get_user_limits(user_id: str):
    """Get rate limits and usage for a user"""
    try:
        tier = request.args.get('tier', 'free')
        limits = rate_limiter.get_user_limits(user_id, tier)

        return jsonify(limits)

    except Exception as e:
        logger.error(f"Failed to get user limits for {user_id}: {e}")
        return jsonify({
            'error': 'Failed to get user limits',
            'message': str(e)
        }), 500

@async_bp.route('/queue/stats', methods=['GET'])
def get_queue_stats():
    """Get queue statistics (admin endpoint)"""
    try:
        # TODO: Add admin authentication
        stats = queue_producer.get_queue_stats()
        job_stats = job_status_manager.get_job_statistics()

        return jsonify({
            'queue_stats': stats,
            'job_stats': job_stats,
            'timestamp': job_stats.get('timestamp')
        })

    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        return jsonify({
            'error': 'Failed to get queue stats',
            'message': str(e)
        }), 500

@async_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        rate_limiter.redis_client.ping()
        job_status_manager.redis_client.ping()

        # Check queue availability
        queue_stats = queue_producer.get_queue_stats()

        return jsonify({
            'status': 'healthy',
            'timestamp': job_status_manager.redis_client.time()[0],
            'queue_available': 'error' not in queue_stats,
            'components': {
                'redis': 'connected',
                'sqs': 'available' if 'error' not in queue_stats else 'error',
                'queue_producer': 'ready',
                'job_status_manager': 'ready'
            }
        })

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

def _download_document_from_url(url: str) -> str:
    """Download document from URL to temporary file"""
    import requests

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.pdf'  # Assume PDF for now
        )

        temp_file.write(response.content)
        temp_file.close()

        return temp_file.name

    except Exception as e:
        logger.error(f"Failed to download document from {url}: {e}")
        raise

def _estimate_processing_time(tier: str, lc_document: Dict[str, Any]) -> str:
    """Estimate processing time based on tier and document complexity"""

    # Base processing times by tier
    base_times = {
        'free': 60,      # 1 minute
        'pro': 30,       # 30 seconds
        'enterprise': 15  # 15 seconds
    }

    base_time = base_times.get(tier, 60)

    # Adjust for document complexity
    complexity_factors = {
        'simple': 1.0,
        'moderate': 1.5,
        'complex': 2.0
    }

    # Simple complexity estimation
    doc_fields = len(lc_document.keys())
    if doc_fields < 10:
        complexity = 'simple'
    elif doc_fields < 20:
        complexity = 'moderate'
    else:
        complexity = 'complex'

    estimated_time = int(base_time * complexity_factors[complexity])

    return f"{estimated_time} seconds"