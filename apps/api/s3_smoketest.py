#!/usr/bin/env python3
"""
AWS S3 Smoke Test Script
Tests S3 configuration by uploading, downloading, and deleting a test file.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv


def load_environment():
    """Load and validate environment variables."""
    # Try to load from .env.production first, then .env
    for env_file in ['.env.production', '.env']:
        if os.path.exists(env_file):
            print(f"📁 Loading environment from {env_file}")
            load_dotenv(env_file)
            break
    else:
        print("⚠️  No .env or .env.production file found, using system environment")
    
    # Check required environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'S3_BUCKET_NAME']
    missing_vars = []
    
    env_vars = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        env_vars[var] = value
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    print(f"🔧 AWS Region: {env_vars['AWS_REGION']}")
    print(f"🪣 S3 Bucket: {env_vars['S3_BUCKET_NAME']}")
    
    return env_vars


def create_s3_client(aws_region, aws_access_key_id, aws_secret_access_key):
    """Create and return an S3 client."""
    try:
        client = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        return client
    except NoCredentialsError:
        print("❌ AWS credentials not found or invalid")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to create S3 client: {e}")
        sys.exit(1)


def test_s3_upload(s3_client, bucket_name, test_key, test_content):
    """Test uploading a file to S3."""
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print("✅ Upload OK")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Upload failed: {error_code} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def test_s3_download(s3_client, bucket_name, test_key):
    """Test downloading a file from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        content = response['Body'].read().decode('utf-8')
        print(f"✅ Download OK: {content}")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Download failed: {error_code} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def test_s3_delete(s3_client, bucket_name, test_key):
    """Test deleting a file from S3."""
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✅ Delete OK")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Delete failed: {error_code} - {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        return False


def main():
    """Main smoke test function."""
    print("🧪 Starting AWS S3 Smoke Test")
    print("=" * 40)
    
    # Load environment variables
    env_vars = load_environment()
    
    # Create S3 client
    s3_client = create_s3_client(
        env_vars['AWS_REGION'],
        env_vars['AWS_ACCESS_KEY_ID'],
        env_vars['AWS_SECRET_ACCESS_KEY']
    )
    
    # Test configuration
    bucket_name = env_vars['S3_BUCKET_NAME']
    test_key = 'health/test.txt'
    test_content = 'hello lcopilot'
    
    print(f"🎯 Testing with key: {test_key}")
    print("=" * 40)
    
    # Run tests
    upload_success = test_s3_upload(s3_client, bucket_name, test_key, test_content)
    
    if not upload_success:
        print("⚠️  Skipping remaining tests due to upload failure")
        sys.exit(1)
    
    download_success = test_s3_download(s3_client, bucket_name, test_key)
    delete_success = test_s3_delete(s3_client, bucket_name, test_key)
    
    # Final result
    print("=" * 40)
    if upload_success and download_success and delete_success:
        print("🎉 All S3 operations successful!")
        print("✅ Your AWS S3 configuration is working correctly")
    else:
        print("❌ Some S3 operations failed")
        sys.exit(1)


if __name__ == '__main__':
    main()