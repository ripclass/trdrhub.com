#!/usr/bin/env python3
"""
Security Tests - S3 KMS Encryption
Tests that S3 uploads use KMS encryption
"""

import unittest
import os
import sys
import tempfile
import importlib
from unittest.mock import patch, MagicMock, call, ANY

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

queue_producer = importlib.import_module("async_tasks.queue_producer")
QueueProducer = queue_producer.QueueProducer
ConfigError = queue_producer.ConfigError

class TestS3KMSEncryption(unittest.TestCase):
    """Test S3 KMS encryption for document uploads"""

    def setUp(self):
        """Set up test environment"""
        # Store original environment
        self.original_env = os.environ.copy()

        # Set required environment variables
        os.environ['AWS_ACCESS_KEY_ID'] = 'test_access_key'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'test_secret_key'
        os.environ['REDIS_PASSWORD'] = 'test_redis_password'

    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_s3_upload_requires_kms_key(self):
        """Test that S3 uploads require KMS_KEY_ID environment variable"""
        # Clear KMS_KEY_ID
        if 'KMS_KEY_ID' in os.environ:
            del os.environ['KMS_KEY_ID']

        with patch('boto3.Session'):
            with patch('redis.Redis'):
                with patch('async.queue_producer.QueueProducer._setup_queues'):
                    producer = QueueProducer()

                    # Create a temp file to upload
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(b'test document content')
                        tmp_file_path = tmp_file.name

                    try:
                        # Should raise ConfigError when trying to upload without KMS_KEY_ID
                        with self.assertRaises(ConfigError) as context:
                            producer._upload_document_to_s3(tmp_file_path, 'test-job-123')

                        self.assertIn("KMS_KEY_ID not found", str(context.exception))
                        self.assertIn("Required for encrypted S3 uploads", str(context.exception))
                    finally:
                        os.unlink(tmp_file_path)

    def test_s3_upload_uses_kms_encryption(self):
        """Test that S3 uploads use KMS encryption with the specified key"""
        # Set KMS_KEY_ID
        os.environ['KMS_KEY_ID'] = 'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012'

        with patch('boto3.Session') as mock_session:
            with patch('redis.Redis'):
                # Mock S3 client
                mock_s3 = MagicMock()
                mock_sqs = MagicMock()
                mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

                producer = QueueProducer()

                # Create a temp file to upload
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(b'test document content for encryption')
                    tmp_file_path = tmp_file.name

                try:
                    # Upload document
                    s3_key = producer._upload_document_to_s3(tmp_file_path, 'test-job-456')

                    # Verify S3 upload was called with KMS encryption
                    mock_s3.upload_fileobj.assert_called_once()
                    call_args = mock_s3.upload_fileobj.call_args

                    # Check ExtraArgs for KMS encryption
                    extra_args = call_args[1]['ExtraArgs']
                    self.assertEqual(extra_args['ServerSideEncryption'], 'aws:kms')
                    self.assertEqual(extra_args['SSEKMSKeyId'],
                                   'arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012')

                    # Check storage class is set
                    self.assertEqual(extra_args['StorageClass'], 'INTELLIGENT_TIERING')

                    # Check metadata is included
                    self.assertIn('job_id', extra_args['Metadata'])
                    self.assertEqual(extra_args['Metadata']['job_id'], 'test-job-456')

                finally:
                    os.unlink(tmp_file_path)

    def test_s3_upload_file_path_format(self):
        """Test that S3 upload uses correct file path format"""
        from datetime import datetime

        os.environ['KMS_KEY_ID'] = 'test-kms-key'

        with patch('boto3.Session') as mock_session:
            with patch('redis.Redis'):
                # Mock S3 client
                mock_s3 = MagicMock()
                mock_sqs = MagicMock()
                mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

                producer = QueueProducer()

                # Create a temp file with specific extension
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(b'test content')
                    tmp_file_path = tmp_file.name

                try:
                    # Upload document
                    s3_key = producer._upload_document_to_s3(tmp_file_path, 'job-789')

                    # Verify S3 key format
                    self.assertTrue(s3_key.startswith('documents/'))
                    self.assertIn('job-789', s3_key)
                    self.assertTrue(s3_key.endswith('.pdf'))

                    # Verify upload was called with correct bucket and key
                    call_args = mock_s3.upload_fileobj.call_args
                    self.assertEqual(call_args[0][1], 'lcopilot-documents')  # Default bucket
                    self.assertTrue(call_args[0][2].startswith('documents/'))

                finally:
                    os.unlink(tmp_file_path)

    def test_s3_bucket_configuration(self):
        """Test that S3 bucket can be configured"""
        os.environ['KMS_KEY_ID'] = 'test-kms-key'

        # Create custom config with different S3 bucket
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = """
storage:
  s3_bucket: custom-document-bucket
"""
            with patch('boto3.Session') as mock_session:
                with patch('redis.Redis'):
                    # Mock S3 client
                    mock_s3 = MagicMock()
                    mock_sqs = MagicMock()
                    mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                    mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

                    producer = QueueProducer()

                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(b'test')
                        tmp_file_path = tmp_file.name

                    try:
                        # Upload document
                        s3_key = producer._upload_document_to_s3(tmp_file_path, 'job-123')

                        # Verify custom bucket was used
                        call_args = mock_s3.upload_fileobj.call_args
                        self.assertEqual(call_args[0][1], 'custom-document-bucket')
                    finally:
                        os.unlink(tmp_file_path)

    def test_s3_upload_error_handling(self):
        """Test that S3 upload errors are properly handled"""
        os.environ['KMS_KEY_ID'] = 'test-kms-key'

        with patch('boto3.Session') as mock_session:
            with patch('redis.Redis'):
                # Mock S3 client that raises an exception
                mock_s3 = MagicMock()
                mock_s3.upload_fileobj.side_effect = Exception("S3 upload failed: Access Denied")
                mock_sqs = MagicMock()
                mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

                producer = QueueProducer()

                # Create a temp file
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(b'test')
                    tmp_file_path = tmp_file.name

                try:
                    # Should raise exception with S3 error
                    with self.assertRaises(Exception) as context:
                        producer._upload_document_to_s3(tmp_file_path, 'job-error')

                    self.assertIn("S3 upload failed", str(context.exception))

                finally:
                    os.unlink(tmp_file_path)

    def test_enqueue_job_full_encryption_flow(self):
        """Test the full enqueue_job flow ensures KMS encryption"""
        import importlib
        queue_producer = importlib.import_module('async.queue_producer')
        QueueProducer = queue_producer.QueueProducer

        os.environ['KMS_KEY_ID'] = 'arn:aws:kms:us-east-1:123456789012:key/full-test-key'

        with patch('boto3.Session') as mock_session:
            with patch('redis.Redis'):
                with patch('async.queue_producer.RateLimiter') as mock_limiter:
                    with patch('async.queue_producer.JobStatusManager') as mock_job_status:
                        # Mock AWS clients
                        mock_s3 = MagicMock()
                        mock_sqs = MagicMock()
                        mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                        mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}
                        mock_sqs.send_message.return_value = {'MessageId': 'msg-123'}

                        # Mock rate limiter
                        mock_limiter.return_value.check_rate_limit.return_value = True

                        producer = QueueProducer()

                        # Create a temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(b'LC document content')
                            tmp_file_path = tmp_file.name

                        try:
                            # Enqueue job
                            job_id = producer.enqueue_job(
                                user_id='user-123',
                                tier='pro',
                                document_path=tmp_file_path,
                                lc_document={'lc_number': 'LC789'},
                                bank_mode='strict'
                            )

                            # Verify S3 upload was called with KMS encryption
                            mock_s3.upload_fileobj.assert_called_once()
                            extra_args = mock_s3.upload_fileobj.call_args[1]['ExtraArgs']

                            # Check all required encryption parameters
                            self.assertEqual(extra_args['ServerSideEncryption'], 'aws:kms')
                            self.assertEqual(extra_args['SSEKMSKeyId'],
                                           'arn:aws:kms:us-east-1:123456789012:key/full-test-key')
                            self.assertEqual(extra_args['StorageClass'], 'INTELLIGENT_TIERING')

                            # Verify job was queued to SQS
                            mock_sqs.send_message.assert_called_once()

                        finally:
                            os.unlink(tmp_file_path)

    def test_kms_key_not_logged(self):
        """Test that KMS key ID is never logged in plaintext"""
        import logging
        import importlib
        queue_producer = importlib.import_module('async.queue_producer')
        QueueProducer = queue_producer.QueueProducer

        os.environ['KMS_KEY_ID'] = 'super-secret-kms-key-id-should-not-appear-in-logs'

        # Capture logs
        with self.assertLogs(level=logging.DEBUG) as logs:
            with patch('boto3.Session') as mock_session:
                with patch('redis.Redis'):
                    # Mock AWS clients
                    mock_s3 = MagicMock()
                    mock_sqs = MagicMock()
                    mock_session.return_value.client.side_effect = [mock_sqs, mock_s3]
                    mock_sqs.get_queue_url.return_value = {'QueueUrl': 'test-queue-url'}

                    producer = QueueProducer()

                    # Create and upload a file
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(b'test')
                        tmp_file_path = tmp_file.name

                    try:
                        producer._upload_document_to_s3(tmp_file_path, 'job-log-test')
                    finally:
                        os.unlink(tmp_file_path)

        # Check that KMS key doesn't appear in logs
        all_logs = '\n'.join(logs.output)
        self.assertNotIn('super-secret-kms-key-id-should-not-appear-in-logs', all_logs)


if __name__ == '__main__':
    unittest.main()
