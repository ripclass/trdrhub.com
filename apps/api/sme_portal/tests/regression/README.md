# LCopilot Trust Platform - Phase 4.5 Regression Tests

## Quick Start

```bash
# Run all regression tests
make test-regression

# Run with HTML reports
make test-regression-html

# Run specific test categories
make test-regression-security
make test-regression-rate-limiting
make test-regression-integration
```

## Test Files Overview

| File | Purpose | Key Features |
|------|---------|--------------|
| `test_security.py` | Security hardening validation | AWS creds, Redis TLS, file upload, S3 KMS |
| `test_rate_limiting.py` | Tier-based rate limiting | Free/Pro limits, burst protection, windows |
| `test_job_cleanup.py` | Resource cleanup testing | Old jobs, async cleanup, scheduling |
| `test_error_handling.py` | Error standardization | Consistent errors, recovery, boundaries |
| `test_correlation_ids.py` | Request tracing | ID consistency, distributed tracing |
| `test_integration_flow.py` | End-to-end workflows | Complete LC validation, service chains |

## Test Results

- **HTML Report**: `test-results/html/regression-report.html`
- **Coverage Report**: `test-results/html/coverage/index.html`
- **JUnit XML**: `test-results/regression-results.xml`

## Key Metrics

- **Total Tests**: 150+ comprehensive test cases
- **Coverage Target**: 85% minimum code coverage
- **Execution Time**: ~2-3 minutes for full suite
- **Mock Dependencies**: All external services mocked

## Critical Test Areas

1. **Security**: AWS credential protection, TLS enforcement, file security
2. **Rate Limiting**: Tier-based limits, burst protection, recovery
3. **Cleanup**: Job lifecycle, resource management, scheduling
4. **Error Handling**: Standardization, logging, recovery mechanisms
5. **Tracing**: Correlation IDs, distributed tracing, consistency
6. **Integration**: End-to-end workflows, service interactions

For detailed documentation, see [REGRESSION_TEST_PLAN.md](../../REGRESSION_TEST_PLAN.md)