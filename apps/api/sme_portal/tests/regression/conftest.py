"""
Pytest configuration and fixtures for LCopilot regression tests.

Provides common fixtures, mocks, and test utilities for regression testing.
"""

import pytest
import tempfile
import json
import os
import uuid
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path


# Test data fixtures
@pytest.fixture
def sample_lc_document():
    """Sample LC document for testing."""
    return {
        "lc_number": "TEST-LC-001",
        "applicant": {
            "name": "Test Company Ltd",
            "address": "123 Test Street, Test City, TC 12345",
            "country": "US"
        },
        "beneficiary": {
            "name": "Supplier Corp",
            "address": "456 Supply Ave, Supply City, SC 67890",
            "country": "CN"
        },
        "amount": {
            "value": 100000.00,
            "currency": "USD"
        },
        "expiry_date": "2024-12-31",
        "documents_required": [
            "Commercial Invoice",
            "Bill of Lading",
            "Certificate of Origin"
        ],
        "latest_shipment_date": "2024-11-30",
        "port_of_loading": "Shanghai",
        "port_of_discharge": "Los Angeles",
        "partial_shipment": "Not Allowed",
        "transshipment": "Not Allowed"
    }


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "customer_id": "test_customer_001",
        "tier": "pro",
        "company_name": "Test Company Ltd",
        "email": "test@testcompany.com",
        "created_at": "2024-01-01T00:00:00Z",
        "limits": {
            "requests_per_minute": 100,
            "requests_per_hour": 2000,
            "requests_per_day": 10000,
            "features": {
                "advanced_compliance": True,
                "bank_profiles": True,
                "evidence_packs": True,
                "async_processing": True
            }
        }
    }


@pytest.fixture
def temp_directory():
    """Temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_correlation_id():
    """Generate mock correlation ID."""
    return f"lcop_test_{int(time.time())}_{str(uuid.uuid4())[:8]}"


@pytest.fixture
def mock_request_id():
    """Generate mock request ID."""
    return f"req_{str(uuid.uuid4())}"


# Mock service fixtures
@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.expirations = {}

        def get(self, key):
            if key in self.expirations and time.time() > self.expirations[key]:
                del self.data[key]
                del self.expirations[key]
                return None
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value
            if ex:
                self.expirations[key] = time.time() + ex
            return True

        def incr(self, key):
            current = int(self.data.get(key, 0))
            self.data[key] = current + 1
            return self.data[key]

        def expire(self, key, seconds):
            self.expirations[key] = time.time() + seconds
            return True

        def ttl(self, key):
            if key not in self.expirations:
                return -1
            remaining = self.expirations[key] - time.time()
            return max(0, int(remaining))

        def delete(self, key):
            self.data.pop(key, None)
            self.expirations.pop(key, None)
            return True

        def ping(self):
            return True

        def flushall(self):
            self.data.clear()
            self.expirations.clear()

    return MockRedis()


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing."""
    class MockS3:
        def __init__(self):
            self.buckets = {}
            self.objects = {}

        def create_bucket(self, Bucket, **kwargs):
            self.buckets[Bucket] = {
                'created': datetime.now(),
                'encryption': None
            }
            return True

        def put_object(self, Bucket, Key, Body, **kwargs):
            if Bucket not in self.buckets:
                raise Exception(f"Bucket {Bucket} does not exist")

            self.objects[f"{Bucket}/{Key}"] = {
                'body': Body,
                'metadata': kwargs,
                'created': datetime.now()
            }
            return {
                'ETag': f'"{hash(str(Body))}"',
                'ServerSideEncryption': kwargs.get('ServerSideEncryption'),
                'SSEKMSKeyId': kwargs.get('SSEKMSKeyId')
            }

        def get_object(self, Bucket, Key):
            obj_key = f"{Bucket}/{Key}"
            if obj_key not in self.objects:
                raise Exception("NoSuchKey")

            obj = self.objects[obj_key]
            return {
                'Body': obj['body'],
                'Metadata': obj['metadata'],
                'ServerSideEncryption': obj['metadata'].get('ServerSideEncryption')
            }

        def head_object(self, Bucket, Key):
            obj_key = f"{Bucket}/{Key}"
            if obj_key not in self.objects:
                raise Exception("NoSuchKey")

            obj = self.objects[obj_key]
            return {
                'ContentLength': len(str(obj['body'])),
                'ServerSideEncryption': obj['metadata'].get('ServerSideEncryption'),
                'SSEKMSKeyId': obj['metadata'].get('SSEKMSKeyId')
            }

        def put_bucket_encryption(self, Bucket, ServerSideEncryptionConfiguration):
            if Bucket not in self.buckets:
                raise Exception(f"Bucket {Bucket} does not exist")

            self.buckets[Bucket]['encryption'] = ServerSideEncryptionConfiguration

        def get_bucket_encryption(self, Bucket):
            if Bucket not in self.buckets:
                raise Exception(f"Bucket {Bucket} does not exist")

            encryption = self.buckets[Bucket]['encryption']
            if not encryption:
                raise Exception("ServerSideEncryptionConfigurationNotFoundError")

            return {'ServerSideEncryptionConfiguration': encryption}

    return MockS3()


@pytest.fixture
def mock_kms_client():
    """Mock KMS client for testing."""
    class MockKMS:
        def __init__(self):
            self.keys = {}

        def create_key(self, Description, Usage='ENCRYPT_DECRYPT'):
            key_id = str(uuid.uuid4())
            self.keys[key_id] = {
                'KeyId': key_id,
                'Description': Description,
                'Usage': Usage,
                'KeyState': 'Enabled',
                'CreationDate': datetime.now(),
                'KeyRotationEnabled': False
            }
            return {
                'KeyMetadata': self.keys[key_id]
            }

        def enable_key_rotation(self, KeyId):
            if KeyId in self.keys:
                self.keys[KeyId]['KeyRotationEnabled'] = True
            return True

        def get_key_rotation_status(self, KeyId):
            if KeyId not in self.keys:
                raise Exception("KeyNotFoundException")

            return {
                'KeyRotationEnabled': self.keys[KeyId]['KeyRotationEnabled']
            }

        def describe_key(self, KeyId):
            if KeyId not in self.keys:
                raise Exception("KeyNotFoundException")

            return {
                'KeyMetadata': self.keys[KeyId]
            }

    return MockKMS()


@pytest.fixture
def mock_tier_manager():
    """Mock tier manager for testing."""
    class MockTierManager:
        def __init__(self):
            self.customers = {}

        def get_tier_info(self, tier):
            tier_configs = {
                'free': {
                    'name': 'Free',
                    'requests_per_minute': 10,
                    'requests_per_hour': 100,
                    'requests_per_day': 500,
                    'advanced_compliance': False,
                    'bank_profiles': False,
                    'evidence_packs': False,
                    'async_processing': False
                },
                'pro': {
                    'name': 'Professional',
                    'requests_per_minute': 100,
                    'requests_per_hour': 2000,
                    'requests_per_day': 10000,
                    'advanced_compliance': True,
                    'bank_profiles': True,
                    'evidence_packs': True,
                    'async_processing': True
                },
                'enterprise': {
                    'name': 'Enterprise',
                    'requests_per_minute': 1000,
                    'requests_per_hour': 50000,
                    'requests_per_day': 1000000,
                    'advanced_compliance': True,
                    'bank_profiles': True,
                    'evidence_packs': True,
                    'async_processing': True
                }
            }
            return type('TierInfo', (), tier_configs.get(tier, tier_configs['free']))()

        def get_customer_summary(self, customer_id, tier):
            return {
                'customer_id': customer_id,
                'tier': tier,
                'usage': {
                    'requests_this_month': 45,
                    'requests_today': 12,
                    'requests_this_hour': 3
                },
                'limits': self.get_tier_info(tier).__dict__
            }

    return MockTierManager()


# Test environment fixtures
@pytest.fixture(autouse=True)
def test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()

    # Set test environment variables
    test_env = {
        'ENVIRONMENT': 'test',
        'FLASK_ENV': 'test',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'REDIS_URL': 'redis://localhost:6379/0',
        'DATABASE_URL': 'sqlite:///:memory:',
        'SECRET_KEY': 'test_secret_key_123456789'
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_logger():
    """Mock logger for testing log outputs."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def regression_test_data():
    """Test data specifically for regression testing."""
    return {
        'valid_lc_documents': [
            {
                "lc_number": "REGRESSION-001",
                "amount": {"value": 50000, "currency": "USD"},
                "expiry_date": "2024-12-31"
            },
            {
                "lc_number": "REGRESSION-002",
                "amount": {"value": 75000, "currency": "EUR"},
                "expiry_date": "2024-11-30"
            }
        ],
        'invalid_lc_documents': [
            {
                "lc_number": "INVALID-001",
                # Missing required fields
            },
            {
                "lc_number": "INVALID-002",
                "amount": {"value": -1000, "currency": "USD"},  # Negative amount
                "expiry_date": "2020-01-01"  # Past date
            }
        ],
        'test_customers': [
            {'id': 'regression_free_001', 'tier': 'free'},
            {'id': 'regression_pro_001', 'tier': 'pro'},
            {'id': 'regression_enterprise_001', 'tier': 'enterprise'}
        ]
    }


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()
            return self.duration

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically cleanup test files after each test."""
    test_files = []

    def register_file(filepath):
        test_files.append(filepath)

    yield register_file

    # Cleanup
    for filepath in test_files:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass  # Ignore cleanup errors


# Pytest hooks for better test reporting
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "critical: marks tests as critical")
    config.addinivalue_line("markers", "security: security-related tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "unit: unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file/function names."""
    for item in items:
        # Add markers based on file names
        if "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "test_rate_limiting" in item.nodeid:
            item.add_marker(pytest.mark.rate_limiting)

        # Add markers based on test names
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)
        if "critical" in item.name:
            item.add_marker(pytest.mark.critical)


# HTML report hooks (uncomment if pytest-html is installed)
# def pytest_html_report_title(report):
#     """Customize HTML report title."""
#     report.title = "LCopilot Trust Platform - Phase 4.5 Regression Tests"
#
#
# def pytest_html_results_summary(prefix, summary, postfix):
#     """Customize HTML report summary."""
#     prefix.extend([
#         "<h2>LCopilot Trust Platform</h2>",
#         "<p>Phase 4.5 Security Hardening - Regression Test Results</p>",
#         "<p>Test Suite Version: 1.0</p>"
#     ])