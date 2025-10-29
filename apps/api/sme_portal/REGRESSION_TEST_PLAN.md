# LCopilot Trust Platform - Phase 4.5 Regression Test Plan

## Overview

This document outlines the comprehensive regression test suite for the LCopilot Trust Platform after Phase 4.5 security hardening. The test suite ensures that security enhancements do not break existing functionality and that new security features work as expected.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Test Categories](#test-categories)
3. [Running Tests](#running-tests)
4. [Test Environment Setup](#test-environment-setup)
5. [Mocking Strategy](#mocking-strategy)
6. [Continuous Integration](#continuous-integration)
7. [Test Results and Reporting](#test-results-and-reporting)
8. [Troubleshooting](#troubleshooting)

## Test Structure

The regression test suite is organized under `tests/regression/` with the following structure:

```
tests/regression/
├── __init__.py
├── test_security.py              # AWS credentials, Redis TLS, file upload, S3 KMS
├── test_rate_limiting.py         # Free vs Pro tier rate limits
├── test_job_cleanup.py           # Old job cleanup processes
├── test_error_handling.py        # Error standardization and recovery
├── test_correlation_ids.py       # Request ID consistency and tracing
└── test_integration_flow.py      # End-to-end integration workflows
```

## Test Categories

### 1. Security Tests (`test_security.py`)

**Purpose**: Validate security hardening measures and data protection.

**Key Test Areas**:
- **AWS Credentials Security**
  - Credentials not exposed in logs
  - Invalid credentials properly rejected
  - Credential rotation support
  - Temporary credentials handling

- **Redis TLS Enforcement**
  - TLS connections required
  - Non-TLS connections rejected
  - Certificate validation
  - Strong encryption algorithms

- **File Upload Security**
  - File size limit enforcement (10MB)
  - File type validation (JSON only)
  - Malicious content scanning
  - Path traversal prevention
  - File quarantine on threat detection

- **S3 KMS Encryption**
  - Objects encrypted with KMS keys
  - Key rotation functionality
  - Bucket encryption policies
  - Access control enforcement

- **Security Headers**
  - Required security headers present
  - CORS policy enforcement
  - Rate limiting headers

**Critical Test Cases**:
```bash
# Run security tests only
make test-regression-security
```

### 2. Rate Limiting Tests (`test_rate_limiting.py`)

**Purpose**: Ensure tier-based rate limiting works correctly.

**Key Test Areas**:
- **Tier-Based Limits**
  - Free tier: 10 req/min, 100 req/hour, 500 req/day
  - Pro tier: 100 req/min, 2000 req/hour, 10000 req/day
  - Enterprise tier: High/unlimited limits

- **Rate Limit Windows**
  - Minute window reset behavior
  - Hour window tracking
  - Day window persistence

- **Burst Protection**
  - Burst traffic detection
  - Mitigation strategies
  - Distributed burst protection

- **Rate Limit Recovery**
  - Window expiration handling
  - Graceful degradation
  - Error response formatting

**Critical Test Cases**:
```bash
# Run rate limiting tests only
make test-regression-rate-limiting
```

### 3. Job Cleanup Tests (`test_job_cleanup.py`)

**Purpose**: Validate job lifecycle management and resource cleanup.

**Key Test Areas**:
- **Basic Job Cleanup**
  - Old completed jobs removal (7+ days)
  - Failed jobs retention (30+ days)
  - Running/pending jobs preservation

- **Async Job Cleanup**
  - Job artifact cleanup
  - Queue message cleanup
  - Dependency cleanup

- **Resource Cleanup**
  - Temporary file removal
  - Memory cache cleanup
  - Database connection cleanup

- **Cleanup Scheduling**
  - Scheduled execution
  - Failure retry logic
  - Concurrent cleanup prevention

### 4. Error Handling Tests (`test_error_handling.py`)

**Purpose**: Ensure consistent error handling and recovery mechanisms.

**Key Test Areas**:
- **Error Standardization**
  - Consistent error response format
  - Standard error codes
  - Message sanitization

- **Error Logging**
  - Context inclusion in logs
  - Stack trace logging
  - Structured logging format

- **Error Recovery**
  - Retry mechanisms for transient errors
  - Circuit breaker patterns
  - Graceful degradation

- **Error Boundaries**
  - Request isolation
  - Async error handling
  - Service fault tolerance

### 5. Correlation ID Tests (`test_correlation_ids.py`)

**Purpose**: Validate request tracing and correlation across services.

**Key Test Areas**:
- **ID Generation**
  - Correlation ID format consistency
  - Request ID uniqueness
  - ID inheritance in child operations

- **Request Tracing**
  - Trace span creation
  - Distributed trace propagation
  - Trace sampling

- **Consistency**
  - Async operation consistency
  - Retry operation consistency
  - Error scenario consistency

- **Trace Aggregation**
  - Correlation ID aggregation
  - Performance metrics extraction
  - Cross-service tracing

### 6. Integration Flow Tests (`test_integration_flow.py`)

**Purpose**: Validate end-to-end workflows and service interactions.

**Key Test Areas**:
- **End-to-End LC Validation**
  - Complete validation workflow
  - Service interaction chain
  - Success and failure scenarios

- **Async Processing Flow**
  - Job submission and processing
  - Status tracking
  - Result notification

- **Service Fault Tolerance**
  - Compliance engine fallback
  - Bank profile degradation
  - Evidence packager retries

- **Data Consistency**
  - Correlation ID propagation
  - Customer tier consistency
  - Cross-service data integrity

## Running Tests

### Quick Start

```bash
# Run all regression tests
make test-regression

# Run with HTML report generation
make test-regression-html

# Run specific test categories
make test-regression-security
make test-regression-rate-limiting
make test-regression-integration
```

### Detailed Test Execution

```bash
# Run all regression tests with verbose output
python -m pytest sme_portal/tests/regression/ -v

# Run specific test file
python -m pytest sme_portal/tests/regression/test_security.py -v

# Run specific test class
python -m pytest sme_portal/tests/regression/test_security.py::TestAWSCredentialsSecurity -v

# Run specific test method
python -m pytest sme_portal/tests/regression/test_security.py::TestAWSCredentialsSecurity::test_aws_credentials_not_exposed_in_logs -v

# Run with coverage report
python -m pytest sme_portal/tests/regression/ -v --cov=sme_portal --cov-report=html
```

### Test Filtering

```bash
# Run only fast tests (exclude slow integration tests)
python -m pytest sme_portal/tests/regression/ -v -m "not slow"

# Run only tests marked as critical
python -m pytest sme_portal/tests/regression/ -v -m "critical"

# Run tests with specific keywords
python -m pytest sme_portal/tests/regression/ -v -k "security"
python -m pytest sme_portal/tests/regression/ -v -k "rate_limit"
```

## Test Environment Setup

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-html
   pip install moto boto3 redis
   ```

2. **Environment Variables**:
   ```bash
   export ENVIRONMENT=test
   export FLASK_ENV=test
   export AWS_DEFAULT_REGION=us-east-1
   ```

3. **Mock Services**: All external services (AWS, Redis) are mocked by default.

### Configuration

Create a test-specific configuration file:

```yaml
# test_config.yaml
environment: test
mock_services:
  aws: true
  redis: true
  external_apis: true

security:
  enforce_tls: true
  file_upload_limits:
    max_size: 10485760  # 10MB
    allowed_types: [".json"]

rate_limiting:
  enabled: true
  tiers:
    free:
      requests_per_minute: 10
      requests_per_hour: 100
      requests_per_day: 500
    pro:
      requests_per_minute: 100
      requests_per_hour: 2000
      requests_per_day: 10000
```

## Mocking Strategy

### External Service Mocking

The test suite uses comprehensive mocking to avoid dependencies on external services:

1. **AWS Services**:
   - Uses `moto` library for S3, KMS, SQS mocking
   - Custom mocks for credential validation

2. **Redis**:
   - Mock Redis client with TTL and expiration logic
   - Simulates connection failures and TLS enforcement

3. **File System**:
   - Temporary directories for file operations
   - Mock file upload and processing

4. **Time and UUIDs**:
   - Deterministic time mocking for consistency
   - UUID generation mocking when needed

### Mock Implementation Examples

```python
# Example: Mock Redis client
class MockRedisClient:
    def __init__(self):
        self.data = {}
        self.expirations = {}

    def incr(self, key):
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    def expire(self, key, seconds):
        self.expirations[key] = time.time() + seconds
        return True

# Example: AWS S3 mocking with moto
@mock_s3
def test_s3_encryption():
    client = boto3.client('s3', region_name='us-east-1')
    # Test S3 operations with encryption
```

## Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/regression-tests.yml
name: Regression Tests
on: [push, pull_request]

jobs:
  regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-html
      - name: Run regression tests
        run: make test-regression-html
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: regression-test-results
          path: test-results/
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: regression-tests
        name: Run critical regression tests
        entry: python -m pytest sme_portal/tests/regression/ -v -m "critical"
        language: system
        pass_filenames: false
```

## Test Results and Reporting

### HTML Reports

The HTML test reports provide comprehensive test results with:

- Test execution summary
- Pass/fail status for each test
- Error messages and stack traces
- Code coverage visualization
- Execution time metrics

Access reports at:
- **Test Results**: `test-results/html/regression-report.html`
- **Coverage Report**: `test-results/html/coverage/index.html`

### JUnit XML Reports

JUnit XML format is generated for CI/CD integration:
- **Results**: `test-results/regression-results.xml`
- **Coverage**: `test-results/regression-coverage.xml`

### Test Metrics

The test suite tracks:
- **Test Coverage**: Minimum 85% coverage required
- **Execution Time**: Individual and total test execution times
- **Success Rate**: Percentage of passing tests
- **Failure Analysis**: Categorization of test failures

### Example Report Structure

```
Regression Test Summary
======================
Total Tests: 156
Passed: 154 (98.7%)
Failed: 2 (1.3%)
Skipped: 0 (0.0%)
Coverage: 87.3%
Duration: 2m 34s

Failed Tests:
- test_security.py::TestRedisTLS::test_certificate_validation
- test_rate_limiting.py::TestConcurrentRequests::test_distributed_rate_limiting

Coverage Breakdown:
- Security Tests: 92.1%
- Rate Limiting: 85.7%
- Job Cleanup: 89.3%
- Error Handling: 91.2%
- Correlation IDs: 83.4%
- Integration Flow: 88.9%
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Issue: Module not found
   # Solution: Ensure PYTHONPATH is set correctly
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Mock Service Failures**
   ```bash
   # Issue: Moto S3 service not starting
   # Solution: Restart moto services or use different ports
   ```

3. **Redis Connection Errors**
   ```bash
   # Issue: Cannot connect to Redis
   # Solution: Ensure Redis mock is properly initialized
   ```

4. **File Permission Errors**
   ```bash
   # Issue: Cannot write to temporary directory
   # Solution: Check file permissions and disk space
   ```

### Debug Mode

Run tests with detailed debug output:

```bash
# Enable debug logging
python -m pytest sme_portal/tests/regression/ -v -s --log-cli-level=DEBUG

# Run with PDB debugger
python -m pytest sme_portal/tests/regression/ -v --pdb
```

### Performance Issues

If tests run slowly:

1. **Parallelize Tests**:
   ```bash
   # Install pytest-xdist
   pip install pytest-xdist

   # Run tests in parallel
   python -m pytest sme_portal/tests/regression/ -v -n auto
   ```

2. **Skip Slow Tests**:
   ```bash
   # Mark slow tests and skip them
   python -m pytest sme_portal/tests/regression/ -v -m "not slow"
   ```

3. **Use Test Fixtures**:
   - Implement proper setup/teardown
   - Share expensive resources across tests

### Test Data Management

For tests requiring specific data:

```python
# Use fixtures for consistent test data
@pytest.fixture
def sample_lc_document():
    return {
        "lc_number": "TEST-LC-001",
        "amount": {"value": 100000, "currency": "USD"},
        # ... other fields
    }

# Use temporary directories
@pytest.fixture
def temp_dir():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
```

## Test Maintenance

### Regular Updates

1. **Monthly Reviews**: Review and update test cases
2. **Dependency Updates**: Keep testing libraries up to date
3. **Mock Updates**: Update mocks to match service changes
4. **Coverage Goals**: Maintain 85%+ test coverage

### New Feature Integration

When adding new features:

1. **Add Corresponding Tests**: New features must include regression tests
2. **Update Documentation**: Update this test plan document
3. **Review Coverage**: Ensure new code is properly tested
4. **Integration Testing**: Add end-to-end tests for new workflows

### Test Refactoring

Periodically refactor tests for:
- **Maintainability**: Keep tests simple and focused
- **Performance**: Optimize slow-running tests
- **Reliability**: Fix flaky tests
- **Coverage**: Remove redundant tests

---

## Conclusion

The LCopilot Trust Platform regression test suite provides comprehensive coverage of security hardening, functional integrity, and performance characteristics. Regular execution of these tests ensures system reliability and helps prevent regressions as the platform evolves.

For questions or issues with the test suite, please contact the development team or create an issue in the project repository.

**Last Updated**: November 2024
**Version**: 1.0
**Test Suite Version**: Phase 4.5