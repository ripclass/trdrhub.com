#!/usr/bin/env python3
"""
Test suite for LCopilot async processing pipeline
Phase 4: Comprehensive testing of SQS/Lambda integration
"""

import pytest
import json
import time
import tempfile
import os
import importlib
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules to test
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

queue_producer = importlib.import_module("async_tasks.queue_producer")
QueueProducer = queue_producer.QueueProducer
QueueError = queue_producer.QueueError
RateLimitExceeded = queue_producer.RateLimitExceeded

job_status_module = importlib.import_module("async_tasks.job_status")
JobStatusManager = job_status_module.JobStatusManager
JobStatus = job_status_module.JobStatus

rate_limiter_module = importlib.import_module("async_tasks.rate_limiter")
RateLimiter = rate_limiter_module.RateLimiter

lambda_worker_module = importlib.import_module("async_tasks.lambda_worker")
DocumentProcessor = lambda_worker_module.DocumentProcessor

class TestQueueProducer:
    """Test the queue producer functionality"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            'async_processing': {
                'sqs': {
                    'queue_name': 'test-queue',
                    'dead_letter_queue': 'test-dlq',
                    'visibility_timeout': 300,
                    'aws_region': 'us-east-1'
                },
                'rate_limits': {
                    'free': {'jobs_per_hour': 10, 'jobs_per_day': 50, 'concurrent_jobs': 2},
                    'pro': {'jobs_per_hour': 100, 'jobs_per_day': 500, 'concurrent_jobs': 5},
                    'enterprise': {'jobs_per_hour': 1000, 'jobs_per_day': 10000, 'concurrent_jobs': 20}
                }
            },
            'storage': {
                's3_bucket': 'test-bucket'
            }
        }

    @pytest.fixture
    def temp_document(self):
        """Create a temporary document for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False)
        temp_file.write("Test document content")
        temp_file.close()
        yield temp_file.name
        os.unlink(temp_file.name)

    @patch('async.queue_producer.yaml.safe_load')
    @patch('async.queue_producer.boto3.client')
    def test_queue_producer_initialization(self, mock_boto3, mock_yaml, mock_config):
        """Test QueueProducer initialization"""
        mock_yaml.return_value = mock_config
        mock_sqs = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_sqs, mock_s3]

        # Mock queue operations
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

        with patch('builtins.open', create=True):
            producer = QueueProducer('test_config.yaml')

        assert producer.queue_name == 'test-queue'
        assert producer.dead_letter_queue == 'test-dlq'
        mock_boto3.assert_called()

    @patch('async.queue_producer.yaml.safe_load')
    @patch('async.queue_producer.boto3.client')
    @patch('async.rate_limiter.RateLimiter')
    @patch('async.job_status.JobStatusManager')
    def test_enqueue_job_success(self, mock_job_status, mock_rate_limiter,
                                 mock_boto3, mock_yaml, mock_config, temp_document):
        """Test successful job enqueuing"""
        mock_yaml.return_value = mock_config

        # Mock AWS clients
        mock_sqs = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_sqs, mock_s3]

        # Mock queue setup
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-id'}

        # Mock rate limiter
        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.check_rate_limit.return_value = True
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        # Mock job status manager
        mock_job_status_instance = Mock()
        mock_job_status_instance.create_job.return_value = True
        mock_job_status.return_value = mock_job_status_instance

        with patch('builtins.open', create=True):
            producer = QueueProducer('test_config.yaml')

        # Mock S3 upload
        with patch.object(producer, '_upload_document_to_s3', return_value='s3-key'):
            job_id = producer.enqueue_job(
                user_id='test-user',
                tier='pro',
                document_path=temp_document,
                lc_document={'lc_number': 'TEST-001'},
                bank_mode='BRAC_BANK'
            )

        assert job_id is not None
        mock_sqs.send_message.assert_called_once()
        mock_rate_limiter_instance.check_rate_limit.assert_called_once()

    @patch('async.queue_producer.yaml.safe_load')
    @patch('async.queue_producer.boto3.client')
    @patch('async.rate_limiter.RateLimiter')
    def test_enqueue_job_rate_limited(self, mock_rate_limiter, mock_boto3, mock_yaml, mock_config):
        """Test job enqueuing with rate limit exceeded"""
        mock_yaml.return_value = mock_config

        # Mock rate limiter to return False
        mock_rate_limiter_instance = Mock()
        mock_rate_limiter_instance.check_rate_limit.return_value = False
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        # Mock AWS clients
        mock_sqs = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_sqs, mock_s3]
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

        with patch('builtins.open', create=True):
            producer = QueueProducer('test_config.yaml')

        with pytest.raises(RateLimitExceeded):
            producer.enqueue_job(
                user_id='test-user',
                tier='free',
                document_path='/tmp/test.pdf',
                lc_document={'lc_number': 'TEST-001'}
            )

    @patch('async.queue_producer.yaml.safe_load')
    @patch('async.queue_producer.boto3.client')
    def test_get_queue_stats(self, mock_boto3, mock_yaml, mock_config):
        """Test getting queue statistics"""
        mock_yaml.return_value = mock_config

        mock_sqs = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = [mock_sqs, mock_s3]

        # Mock queue attributes
        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}
        mock_sqs.get_queue_attributes.return_value = {
            'Attributes': {
                'ApproximateNumberOfMessages': '5',
                'ApproximateNumberOfMessagesNotVisible': '2',
                'ApproximateNumberOfMessagesDelayed': '0',
                'VisibilityTimeout': '300'
            }
        }

        with patch('builtins.open', create=True):
            producer = QueueProducer('test_config.yaml')

        stats = producer.get_queue_stats()

        assert stats['approximate_messages'] == 5
        assert stats['messages_in_flight'] == 2
        assert stats['visibility_timeout'] == 300

class TestJobStatusManager:
    """Test job status management functionality"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = None
        mock_redis.lpush.return_value = 1
        mock_redis.expire.return_value = True
        return mock_redis

    @patch('async.job_status.yaml.safe_load')
    @patch('async.job_status.redis.Redis')
    def test_job_status_manager_init(self, mock_redis_class, mock_yaml):
        """Test JobStatusManager initialization"""
        mock_config = {
            'redis': {'host': 'localhost', 'port': 6379, 'db': 1},
            'async_processing': {
                'job_status': {
                    'default_ttl': 604800,
                    'polling_interval': 2000
                }
            }
        }
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = Mock()

        with patch('builtins.open', create=True):
            manager = JobStatusManager('test_config.yaml')

        assert manager.default_ttl == 604800
        assert manager.polling_interval == 2000

    @patch('async.job_status.yaml.safe_load')
    @patch('async.job_status.redis.Redis')
    def test_create_job(self, mock_redis_class, mock_yaml, mock_redis):
        """Test job creation"""
        mock_config = {'redis': {}, 'async_processing': {'job_status': {}}}
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        with patch('builtins.open', create=True):
            manager = JobStatusManager('test_config.yaml')

        success = manager.create_job('test-job-123', {
            'user_id': 'test-user',
            'tier': 'pro',
            'status': JobStatus.QUEUED.value
        })

        assert success == True
        mock_redis.setex.assert_called()
        mock_redis.lpush.assert_called()

    @patch('async.job_status.yaml.safe_load')
    @patch('async.job_status.redis.Redis')
    def test_update_job_status(self, mock_redis_class, mock_yaml, mock_redis):
        """Test job status updates"""
        mock_config = {'redis': {}, 'async_processing': {'job_status': {}}}
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        # Mock existing job data
        existing_job = {
            'job_id': 'test-job-123',
            'status': JobStatus.QUEUED.value,
            'updates': []
        }
        mock_redis.get.return_value = json.dumps(existing_job)

        with patch('builtins.open', create=True):
            manager = JobStatusManager('test_config.yaml')

        success = manager.update_job_status('test-job-123', {
            'status': JobStatus.PROCESSING.value,
            'progress': 50,
            'message': 'Processing document'
        })

        assert success == True
        mock_redis.setex.assert_called()

    @patch('async.job_status.yaml.safe_load')
    @patch('async.job_status.redis.Redis')
    def test_get_job_status(self, mock_redis_class, mock_yaml, mock_redis):
        """Test retrieving job status"""
        mock_config = {'redis': {}, 'async_processing': {'job_status': {}}}
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        job_data = {
            'job_id': 'test-job-123',
            'status': JobStatus.COMPLETED.value,
            'progress': 100,
            'results': {'compliance_score': 0.95}
        }
        mock_redis.get.return_value = json.dumps(job_data)

        with patch('builtins.open', create=True):
            manager = JobStatusManager('test_config.yaml')

        retrieved_data = manager.get_job_status('test-job-123')

        assert retrieved_data['job_id'] == 'test-job-123'
        assert retrieved_data['status'] == JobStatus.COMPLETED.value
        assert retrieved_data['results']['compliance_score'] == 0.95

class TestRateLimiter:
    """Test rate limiting functionality"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_redis = Mock()
        mock_redis.get.return_value = '0'  # Default count
        mock_redis.smembers.return_value = set()  # No concurrent jobs
        mock_redis.scard.return_value = 0
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        return mock_redis

    @patch('async.rate_limiter.yaml.safe_load')
    @patch('async.rate_limiter.redis.Redis')
    def test_rate_limiter_init(self, mock_redis_class, mock_yaml, mock_redis):
        """Test RateLimiter initialization"""
        mock_config = {
            'redis': {'host': 'localhost', 'port': 6379, 'db': 0},
            'async_processing': {
                'rate_limits': {
                    'free': {'jobs_per_hour': 10, 'jobs_per_day': 50, 'concurrent_jobs': 2}
                }
            }
        }
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        with patch('builtins.open', create=True):
            limiter = RateLimiter('test_config.yaml')

        assert limiter.rate_limits['free']['jobs_per_hour'] == 10

    @patch('async.rate_limiter.yaml.safe_load')
    @patch('async.rate_limiter.redis.Redis')
    def test_check_rate_limit_success(self, mock_redis_class, mock_yaml, mock_redis):
        """Test successful rate limit check"""
        mock_config = {
            'async_processing': {
                'rate_limits': {
                    'pro': {'jobs_per_hour': 100, 'jobs_per_day': 500, 'concurrent_jobs': 5}
                }
            }
        }
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        # Mock low usage counts
        mock_redis.get.return_value = '5'  # Well below limits
        mock_redis.scard.return_value = 1   # 1 concurrent job (below limit of 5)

        with patch('builtins.open', create=True):
            limiter = RateLimiter('test_config.yaml')

        result = limiter.check_rate_limit('test-user', 'pro')
        assert result == True

    @patch('async.rate_limiter.yaml.safe_load')
    @patch('async.rate_limiter.redis.Redis')
    def test_check_rate_limit_exceeded(self, mock_redis_class, mock_yaml, mock_redis):
        """Test rate limit exceeded"""
        mock_config = {
            'async_processing': {
                'rate_limits': {
                    'free': {'jobs_per_hour': 10, 'jobs_per_day': 50, 'concurrent_jobs': 2}
                }
            }
        }
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        # Mock high usage - exceed hourly limit
        mock_redis.get.return_value = '15'  # Above limit of 10

        with patch('builtins.open', create=True):
            limiter = RateLimiter('test_config.yaml')

        result = limiter.check_rate_limit('test-user', 'free')
        assert result == False

    @patch('async.rate_limiter.yaml.safe_load')
    @patch('async.rate_limiter.redis.Redis')
    def test_record_request(self, mock_redis_class, mock_yaml, mock_redis):
        """Test request recording"""
        mock_config = {'async_processing': {'rate_limits': {}}}
        mock_yaml.return_value = mock_config
        mock_redis_class.return_value = mock_redis

        # Mock pipeline
        mock_pipeline = Mock()
        mock_redis.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [1, True, 1, True]

        with patch('builtins.open', create=True):
            limiter = RateLimiter('test_config.yaml')

        limiter.record_request('test-user', 'pro', 'job-123')

        # Verify pipeline operations were called
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.execute.assert_called_once()

class TestDocumentProcessor:
    """Test Lambda document processor"""

    @pytest.fixture
    def mock_lambda_context(self):
        """Mock Lambda context"""
        context = Mock()
        context.aws_request_id = 'test-request-id'
        return context

    @pytest.fixture
    def sample_job_data(self):
        """Sample job data for testing"""
        return {
            'job_id': 'test-job-123',
            'user_id': 'test-user',
            'tier': 'pro',
            'document_path': 'documents/test-doc.pdf',
            'document_hash': 'abc123',
            'lc_document': {
                'lc_number': 'TEST-LC-001',
                'amount': {'value': 100000, 'currency': 'USD'},
                'issue_date': '2024-01-15'
            },
            'bank_mode': 'BRAC_BANK',
            'options': {}
        }

    @patch.dict(os.environ, {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'})
    @patch('async.lambda_worker.boto3.client')
    def test_document_processor_init(self, mock_boto3):
        """Test DocumentProcessor initialization in Lambda environment"""
        # Mock S3 config response
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: b'platform:\n  name: "Test"')
        }
        mock_boto3.return_value = mock_s3

        with patch('async.lambda_worker.JobStatusManager'), \
             patch('async.lambda_worker.RateLimiter'), \
             patch('async.lambda_worker.TextractFallback'), \
             patch('async.lambda_worker.ComplianceValidator'), \
             patch('async.lambda_worker.BankProfileEngine'):

            processor = DocumentProcessor()

        assert processor.config is not None
        mock_boto3.assert_called()

    @patch('async.lambda_worker.JobStatusManager')
    @patch('async.lambda_worker.RateLimiter')
    @patch('async.lambda_worker.TextractFallback')
    @patch('async.lambda_worker.ComplianceValidator')
    @patch('async.lambda_worker.BankProfileEngine')
    @patch('async.lambda_worker.boto3.client')
    def test_process_job_success(self, mock_boto3, mock_bank_engine, mock_validator,
                                mock_textract, mock_rate_limiter, mock_job_status,
                                sample_job_data, mock_lambda_context):
        """Test successful job processing"""

        # Mock all dependencies
        mock_job_status_instance = Mock()
        mock_job_status.return_value = mock_job_status_instance

        mock_rate_limiter_instance = Mock()
        mock_rate_limiter.return_value = mock_rate_limiter_instance

        mock_textract_instance = Mock()
        mock_textract.return_value = mock_textract_instance

        mock_validator_instance = Mock()
        mock_validator_instance.validate_lc.return_value = {
            'compliance_score': 0.95,
            'overall_status': 'compliant',
            'validated_rules': []
        }
        mock_validator.return_value = mock_validator_instance

        mock_bank_engine_instance = Mock()
        mock_bank_engine_instance.get_profile.return_value = {'bank_name': 'BRAC Bank'}
        mock_bank_engine.return_value = mock_bank_engine_instance

        # Mock S3 client
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3

        with patch('async.lambda_worker.tempfile.NamedTemporaryFile') as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = '/tmp/test-doc.pdf'

            with patch.object(DocumentProcessor, '_load_local_config', return_value={}):
                processor = DocumentProcessor()

            # Mock methods
            with patch.object(processor, '_download_document', return_value='/tmp/test-doc.pdf'), \
                 patch.object(processor, '_extract_document_data', return_value={'text': 'test', 'confidence': 0.9}), \
                 patch.object(processor, '_cleanup_temp_files'):

                result = processor.process_job(sample_job_data, mock_lambda_context)

        assert result['success'] == True
        assert result['job_id'] == 'test-job-123'
        assert 'processing_time' in result

        # Verify job status updates were called
        mock_job_status_instance.update_job_status.assert_called()

    def test_sqs_event_processing(self, sample_job_data, mock_lambda_context):
        """Test SQS event processing with multiple records"""

        sqs_event = {
            'Records': [
                {
                    'body': json.dumps(sample_job_data),
                    'receiptHandle': 'test-receipt-handle-1'
                }
            ]
        }

        with patch.object(DocumentProcessor, '_load_local_config', return_value={}), \
             patch.object(DocumentProcessor, '__init__', return_value=None), \
             patch.object(DocumentProcessor, 'process_job') as mock_process_job:

            mock_process_job.return_value = {
                'success': True,
                'job_id': 'test-job-123',
                'processing_time': 1.5
            }

            processor = DocumentProcessor()
            result = processor.process_sqs_event(sqs_event, mock_lambda_context)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['processed'] == 1
        assert len(body['results']) == 1

def test_lambda_handler():
    """Test the main Lambda handler function"""
    from async_tasks.lambda_worker import lambda_handler

    mock_event = {
        'Records': [{
            'body': json.dumps({
                'job_id': 'test-job',
                'user_id': 'test-user',
                'tier': 'pro',
                'document_path': 'test.pdf',
                'lc_document': {'lc_number': 'TEST'}
            }),
            'receiptHandle': 'test-handle'
        }]
    }

    mock_context = Mock()
    mock_context.aws_request_id = 'test-request'

    with patch('async.lambda_worker.DocumentProcessor') as mock_processor_class:
        mock_processor = Mock()
        mock_processor.process_sqs_event.return_value = {
            'statusCode': 200,
            'body': json.dumps({'processed': 1})
        }
        mock_processor_class.return_value = mock_processor

        result = lambda_handler(mock_event, mock_context)

    assert result['statusCode'] == 200

if __name__ == "__main__":
    pytest.main([__file__])
