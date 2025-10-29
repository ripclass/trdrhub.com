# LCopilot Trust Platform - Regression Test Plan

## Overview

This document outlines the comprehensive regression test suite for the LCopilot Trust Platform following Phase 4.5 security hardening. The test suite ensures all critical security fixes, medium-priority improvements, and backward compatibility are maintained.

## Test Coverage Matrix

### Critical Security Fixes

| Fix Category | Implementation | Test Coverage | Test File |
|--------------|---------------|---------------|-----------|
| AWS Credential Handling | Explicit env vars required | ✅ test_aws_credentials_env_required() | test_security.py |
| Redis TLS/Password | Mandatory authentication | ✅ test_redis_tls_required() | test_security.py |
| File Upload Validation | 10MB size limit | ✅ test_file_upload_size_limit() | test_security.py |
| S3 KMS Encryption | Required for all uploads | ✅ test_s3_upload_kms_encryption() | test_security.py |

### Medium Priority Fixes

| Fix Category | Implementation | Test Coverage | Test File |
|--------------|---------------|---------------|-----------|
| Rate Limiting | Tier-based limits | ✅ test_rate_limiting_free_vs_pro() | test_rate_limiting.py |
| Job Cleanup | 7+ day removal | ✅ test_job_cleanup_removes_old_entries() | test_job_cleanup.py |
| Error Standardization | JSON format | ✅ test_error_standardization_format() | test_error_handling.py |
| Correlation IDs | Request tracking | ✅ test_correlation_id_consistency() | test_correlation_ids.py |

### Integration Flows

| Flow | Description | Test Coverage | Test File |
|------|-------------|---------------|-----------|
| LC Validation | End-to-end with bank profiles | ✅ test_end_to_end_validate_with_bank_profile() | test_integration_flow.py |
| Async Pipeline | OCR fallback & job tracking | ✅ test_end_to_end_async_pipeline_with_fallback() | test_integration_flow.py |
| Evidence Pack | Tamper-proof generation | ✅ test_evidence_pack_generation_and_signature() | test_integration_flow.py |

## Test Suite Structure

```
tests/regression/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_security.py               # AWS, Redis, Upload, S3 security tests
├── test_rate_limiting.py          # Tier-based rate limit tests
├── test_job_cleanup.py            # Async job lifecycle tests
├── test_error_handling.py         # Error standardization tests
├── test_correlation_ids.py        # Request tracking tests
├── test_integration_flow.py       # End-to-end workflow tests
└── README.md                      # Quick start guide
```

## Running Tests Locally

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-html pytest-xdist pytest-timeout

# Set environment variables (use test values)
export AWS_ACCESS_KEY_ID="test_key"
export AWS_SECRET_ACCESS_KEY="test_secret"
export REDIS_PASSWORD="test_password"
export KMS_KEY_ID="test_kms_key"
```

### Running All Regression Tests

```bash
# Run all regression tests with coverage
make test-regression

# Generate HTML report
make test-regression-html

# Run tests in parallel (faster)
pytest tests/regression/ -n auto
```

### Running Specific Test Categories

```bash
# Security tests only
make test-regression-security

# Rate limiting tests only
make test-regression-rate-limiting

# Integration tests only
make test-regression-integration

# Individual test file
pytest tests/regression/test_security.py -v
```

### Running with Coverage

```bash
# Generate coverage report
pytest tests/regression/ --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Regression Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  regression:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-html

    - name: Run regression tests
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        REDIS_PASSWORD: ${{ secrets.REDIS_PASSWORD }}
        KMS_KEY_ID: ${{ secrets.KMS_KEY_ID }}
      run: |
        make test-regression-html

    - name: Upload test results
      uses: actions/upload-artifact@v2
      if: always()
      with:
        name: regression-test-results
        path: |
          test-results/html/
          htmlcov/
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any

    triggers {
        cron('H 2 * * *')  // Nightly
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pip install pytest pytest-cov pytest-html'
            }
        }

        stage('Regression Tests') {
            steps {
                withCredentials([
                    string(credentialsId: 'aws-key', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret', variable: 'AWS_SECRET_ACCESS_KEY'),
                    string(credentialsId: 'redis-password', variable: 'REDIS_PASSWORD'),
                    string(credentialsId: 'kms-key', variable: 'KMS_KEY_ID')
                ]) {
                    sh 'make test-regression-html'
                }
            }
        }

        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: 'test-results/**/*', allowEmptyArchive: true
                publishHTML target: [
                    reportDir: 'test-results/html',
                    reportFiles: 'regression-report.html',
                    reportName: 'Regression Test Report'
                ]
            }
        }
    }
}
```

## Pass/Fail Criteria

### Production Deployment Requirements

Before any production deployment, the following criteria MUST be met:

1. **100% Pass Rate** - All regression tests must pass
2. **Coverage Threshold** - Minimum 85% code coverage
3. **Performance** - Tests complete within 10 minutes
4. **No Critical Issues** - Zero security or data integrity failures

### Test Categories and Weights

| Category | Weight | Required Pass Rate |
|----------|--------|-------------------|
| Security Tests | 40% | 100% |
| Integration Tests | 30% | 100% |
| Rate Limiting | 10% | 100% |
| Job Cleanup | 10% | 95% |
| Error Handling | 5% | 95% |
| Correlation IDs | 5% | 95% |

## Test Reports

### HTML Report Structure

```
test-results/
├── html/
│   ├── regression-report.html     # Main test report
│   ├── coverage/
│   │   └── index.html             # Coverage report
│   └── assets/                   # Report assets
├── xml/
│   ├── junit.xml                  # JUnit format for CI
│   └── coverage.xml               # Coverage data
└── logs/
    └── regression.log             # Detailed test logs
```

### Report Interpretation

#### Test Summary Section
- **Passed**: Tests that executed successfully
- **Failed**: Tests that encountered assertions failures
- **Skipped**: Tests skipped due to conditions
- **Error**: Tests that failed due to exceptions

#### Coverage Metrics
- **Line Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of decision branches tested
- **Function Coverage**: Percentage of functions called

### Example Report Analysis

```
========================== Test Summary ==========================
Platform: LCopilot Trust Platform v2.4.0
Test Run: 2024-09-14 12:00:00 UTC
Environment: Staging

RESULTS:
- Total Tests: 156
- Passed: 154 (98.7%)
- Failed: 2 (1.3%)
- Skipped: 0
- Duration: 8m 32s

COVERAGE:
- Line Coverage: 87.3%
- Branch Coverage: 82.1%
- Function Coverage: 91.2%

FAILED TESTS:
1. test_rate_limiting.py::test_distributed_rate_limiting_consistency
   - Reason: Redis mock timing issue
   - Priority: Medium

2. test_integration_flow.py::test_async_pipeline_timeout_handling
   - Reason: Lambda timeout simulation
   - Priority: Low

RECOMMENDATION: Safe to deploy with known issues documented
==================================================================
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors
```python
# Problem: ImportError for async module
# Solution: Use importlib
import importlib
async_module = importlib.import_module('async.queue_producer')
```

#### 2. Mock Configuration
```python
# Problem: External service calls in tests
# Solution: Ensure all mocks are properly configured
@patch('boto3.Session')
@patch('redis.Redis')
def test_function(mock_redis, mock_session):
    # Test implementation
```

#### 3. Test Isolation
```python
# Problem: Tests affecting each other
# Solution: Use fixtures with proper cleanup
@pytest.fixture(autouse=True)
def cleanup():
    yield
    # Cleanup code here
```

#### 4. Timeout Issues
```python
# Problem: Tests hanging
# Solution: Use pytest timeout
@pytest.mark.timeout(30)
def test_long_running_operation():
    # Test implementation
```

## Maintenance

### Regular Updates

1. **Weekly**: Review failed tests from nightly runs
2. **Monthly**: Update test data and fixtures
3. **Quarterly**: Review coverage thresholds
4. **Per Release**: Add tests for new features

### Test Data Management

```bash
# Refresh test fixtures
python scripts/refresh_test_data.py

# Generate new mock data
python scripts/generate_mock_data.py --type=lc_documents --count=100

# Clean old test artifacts
make clean-test-artifacts
```

## Contact

For questions or issues with regression tests:

- **Test Team**: testing@lcopilot.com
- **DevOps**: ops@lcopilot.com
- **Security**: security@lcopilot.com

## Appendix

### A. Test Markers

```python
# Available pytest markers
@pytest.mark.security      # Security-related tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow          # Tests taking > 5 seconds
@pytest.mark.critical      # Must-pass for production
@pytest.mark.regression    # All regression tests
```

### B. Environment Variables

```bash
# Required for tests
AWS_ACCESS_KEY_ID          # AWS credentials
AWS_SECRET_ACCESS_KEY       # AWS credentials
REDIS_PASSWORD              # Redis authentication
KMS_KEY_ID                  # S3 encryption key

# Optional configuration
TEST_ENVIRONMENT            # test/staging/production
PYTEST_PARALLEL_WORKERS     # Number of parallel workers
TEST_TIMEOUT                # Global test timeout (seconds)
```

### C. Useful Commands

```bash
# Run tests with specific marker
pytest -m security

# Run tests with verbose output
pytest -vv

# Run failed tests only
pytest --lf

# Run tests with pdb on failure
pytest --pdb

# Generate allure report
pytest --alluredir=allure-results
allure serve allure-results
```