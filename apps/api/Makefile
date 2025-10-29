# LCopilot Trust Platform - Phase 4 Deployment Makefile
# Comprehensive build, test, and deployment automation

.PHONY: help install test lint format clean build deploy-local deploy-staging deploy-prod
.PHONY: setup-aws deploy-async setup-monitoring dev-sandbox test-ocr portal-reload
.PHONY: docker-build docker-run docker-push lambda-package lambda-deploy
.PHONY: backup-db migrate-db seed-data test-regression test-regression-html

# Default target
help: ## Show this help message
	@echo "LCopilot Trust Platform - Phase 4 Deployment"
	@echo "=============================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# Configuration
PROJECT_NAME := lcopilot-trust-platform
VERSION := 2.4.0
AWS_REGION := us-east-1
PYTHON := python3
PIP := pip3
DOCKER_REGISTRY := your-registry.amazonaws.com
LAMBDA_FUNCTION_NAME := lcopilot-document-processor

# Environment detection
ENV := $(shell echo $${ENVIRONMENT:-development})
ifeq ($(ENV),production)
    CONFIG_SUFFIX := .prod
else ifeq ($(ENV),staging)
    CONFIG_SUFFIX := .staging
else
    CONFIG_SUFFIX := .dev
endif

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# Installation and Setup
install: ## Install all dependencies
	@echo "$(BLUE)Installing Python dependencies...$(RESET)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

install-redis: ## Install and start Redis (macOS)
	@echo "$(BLUE)Installing Redis...$(RESET)"
	brew install redis
	brew services start redis
	@echo "$(GREEN)✓ Redis installed and started$(RESET)"

setup-env: ## Setup environment configuration
	@echo "$(BLUE)Setting up environment configuration...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)⚠ Please edit .env with your configuration$(RESET)"; \
	fi
	@echo "$(GREEN)✓ Environment setup complete$(RESET)"

# Development
dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(RESET)"
	@make install-redis || echo "$(YELLOW)Redis may already be running$(RESET)"
	@echo "$(GREEN)Starting Flask development server...$(RESET)"
	cd sme_portal && FLASK_ENV=development $(PYTHON) app.py &
	@echo "$(GREEN)Starting main API server...$(RESET)"
	ENVIRONMENT=development $(PYTHON) main.py &
	@echo "$(GREEN)✓ Development environment started$(RESET)"
	@echo "$(BLUE)Portal: http://localhost:5001$(RESET)"
	@echo "$(BLUE)API: http://localhost:5000$(RESET)"

dev-stop: ## Stop development servers
	@echo "$(BLUE)Stopping development servers...$(RESET)"
	pkill -f "python.*app.py" || true
	pkill -f "python.*main.py" || true
	@echo "$(GREEN)✓ Development servers stopped$(RESET)"

dev-sandbox: ## Start developer sandbox with mocks
	@echo "$(BLUE)Starting developer sandbox...$(RESET)"
	@cp trust_config.yaml trust_config.yaml.backup
	@sed -i.bak 's/enabled: false/enabled: true/g' trust_config.yaml
	@sed -i.bak 's/mock_aws_services: true/mock_aws_services: true/g' trust_config.yaml
	@echo "$(GREEN)✓ Sandbox mode enabled$(RESET)"
	@make dev

portal-reload: ## Reload SME Portal with latest changes
	@echo "$(BLUE)Reloading SME Portal...$(RESET)"
	pkill -f "flask.*app.py" || true
	sleep 2
	cd sme_portal && FLASK_ENV=development $(PYTHON) app.py &
	@echo "$(GREEN)✓ SME Portal reloaded$(RESET)"

# Testing
test: ## Run comprehensive test suite
	@echo "$(BLUE)Running test suite...$(RESET)"
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Tests completed$(RESET)"

test-fast: ## Run fast tests only
	@echo "$(BLUE)Running fast tests...$(RESET)"
	$(PYTHON) -m pytest tests/ -v -m "not slow"
	@echo "$(GREEN)✓ Fast tests completed$(RESET)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(RESET)"
	$(PYTHON) -m pytest tests/integration/ -v
	@echo "$(GREEN)✓ Integration tests completed$(RESET)"

test-ocr: ## Test OCR fallback system
	@echo "$(BLUE)Testing OCR fallback system...$(RESET)"
	$(PYTHON) -m pytest tests/test_textract_fallback.py -v
	@echo "$(PYTHON) tests/test_textract_integration.py"
	@echo "$(GREEN)✓ OCR tests completed$(RESET)"

test-async: ## Test async processing pipeline
	@echo "$(BLUE)Testing async processing pipeline...$(RESET)"
	$(PYTHON) -m pytest tests/async/ -v
	@echo "$(GREEN)✓ Async pipeline tests completed$(RESET)"

test-regression: ## Run Phase 4.5 regression test suite
	@echo "$(BLUE)Running Phase 4.5 regression test suite...$(RESET)"
	@echo "Testing security hardening, rate limiting, job cleanup, error handling..."
	$(PYTHON) -m pytest sme_portal/tests/regression/ -v --tb=short \
		--junitxml=test-results/regression-results.xml \
		--cov=sme_portal --cov-report=term \
		--cov-report=xml:test-results/regression-coverage.xml
	@echo "$(GREEN)✓ Regression tests completed$(RESET)"
	@echo "$(BLUE)Results: test-results/regression-results.xml$(RESET)"
	@echo "$(BLUE)Coverage: test-results/regression-coverage.xml$(RESET)"

test-regression-html: ## Run regression tests with HTML report
	@echo "$(BLUE)Running regression tests with HTML report generation...$(RESET)"
	@mkdir -p test-results/html
	$(PYTHON) -m pytest sme_portal/tests/regression/ -v \
		--html=test-results/html/regression-report.html --self-contained-html \
		--junitxml=test-results/regression-results.xml \
		--cov=sme_portal --cov-report=html:test-results/html/coverage \
		--cov-report=term --cov-report=xml:test-results/regression-coverage.xml
	@echo "$(GREEN)✓ Regression tests completed with HTML report$(RESET)"
	@echo "$(BLUE)HTML Report: test-results/html/regression-report.html$(RESET)"
	@echo "$(BLUE)Coverage Report: test-results/html/coverage/index.html$(RESET)"

test-regression-security: ## Run security-specific regression tests
	@echo "$(BLUE)Running security regression tests...$(RESET)"
	$(PYTHON) -m pytest sme_portal/tests/regression/test_security.py -v --tb=short
	@echo "$(GREEN)✓ Security regression tests completed$(RESET)"

test-regression-rate-limiting: ## Run rate limiting regression tests
	@echo "$(BLUE)Running rate limiting regression tests...$(RESET)"
	$(PYTHON) -m pytest sme_portal/tests/regression/test_rate_limiting.py -v --tb=short
	@echo "$(GREEN)✓ Rate limiting regression tests completed$(RESET)"

test-regression-integration: ## Run integration flow regression tests
	@echo "$(BLUE)Running integration flow regression tests...$(RESET)"
	$(PYTHON) -m pytest sme_portal/tests/regression/test_integration_flow.py -v --tb=short
	@echo "$(GREEN)✓ Integration flow regression tests completed$(RESET)"

# Code Quality
lint: ## Run linting and code analysis
	@echo "$(BLUE)Running linting...$(RESET)"
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "$(GREEN)✓ Linting completed$(RESET)"

format: ## Format code with black
	@echo "$(BLUE)Formatting code...$(RESET)"
	black . --line-length=127
	isort . --profile black
	@echo "$(GREEN)✓ Code formatted$(RESET)"

security-scan: ## Run security scan
	@echo "$(BLUE)Running security scan...$(RESET)"
	bandit -r . -ll
	safety check
	@echo "$(GREEN)✓ Security scan completed$(RESET)"

# AWS Setup and Deployment
setup-aws: ## Setup AWS infrastructure
	@echo "$(BLUE)Setting up AWS infrastructure...$(RESET)"
	@echo "Creating S3 buckets..."
	aws s3 mb s3://lcopilot-documents --region $(AWS_REGION) || true
	aws s3 mb s3://lcopilot-config --region $(AWS_REGION) || true
	@echo "Creating SQS queues..."
	aws sqs create-queue --queue-name lcopilot-processing-queue --region $(AWS_REGION) || true
	aws sqs create-queue --queue-name lcopilot-dlq --region $(AWS_REGION) || true
	@echo "$(GREEN)✓ AWS infrastructure setup complete$(RESET)"

deploy-config: ## Deploy configuration to S3
	@echo "$(BLUE)Deploying configuration...$(RESET)"
	aws s3 cp trust_config$(CONFIG_SUFFIX).yaml s3://lcopilot-config/trust_config.yaml --region $(AWS_REGION)
	@echo "$(GREEN)✓ Configuration deployed$(RESET)"

lambda-package: ## Package Lambda function
	@echo "$(BLUE)Packaging Lambda function...$(RESET)"
	@mkdir -p build/lambda
	@cp -r async/ build/lambda/
	@cp -r trust_platform/ build/lambda/
	@cp -r ocr/ build/lambda/
	@cp requirements-lambda.txt build/lambda/requirements.txt
	cd build/lambda && $(PIP) install -r requirements.txt -t .
	cd build/lambda && zip -r ../lcopilot-lambda.zip .
	@echo "$(GREEN)✓ Lambda package created: build/lcopilot-lambda.zip$(RESET)"

lambda-deploy: lambda-package ## Deploy Lambda function
	@echo "$(BLUE)Deploying Lambda function...$(RESET)"
	aws lambda update-function-code \
		--function-name $(LAMBDA_FUNCTION_NAME) \
		--zip-file fileb://build/lcopilot-lambda.zip \
		--region $(AWS_REGION)
	@echo "$(GREEN)✓ Lambda function deployed$(RESET)"

deploy-async: setup-aws lambda-deploy ## Deploy complete async processing pipeline
	@echo "$(BLUE)Deploying async processing pipeline...$(RESET)"
	@make deploy-config
	@echo "$(GREEN)✓ Async processing pipeline deployed$(RESET)"

# Monitoring and Alerts
setup-monitoring: ## Setup CloudWatch monitoring and alerts
	@echo "$(BLUE)Setting up monitoring and alerts...$(RESET)"
	@echo "Creating CloudWatch alarms..."
	aws cloudwatch put-metric-alarm \
		--alarm-name "LCopilot-TextractFallbackRate" \
		--alarm-description "High Textract fallback rate" \
		--metric-name "TextractFallbackRate" \
		--namespace "LCopilot/TrustPlatform" \
		--statistic "Average" \
		--period 3600 \
		--threshold 10.0 \
		--comparison-operator "GreaterThanThreshold" \
		--evaluation-periods 2 \
		--region $(AWS_REGION) || true
	@echo "$(GREEN)✓ Monitoring setup complete$(RESET)"

# Docker Operations
docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(RESET)"
	docker build -t $(PROJECT_NAME):$(VERSION) .
	docker build -t $(PROJECT_NAME)-portal:$(VERSION) -f docker/Dockerfile.portal .
	@echo "$(GREEN)✓ Docker images built$(RESET)"

docker-run: ## Run Docker containers locally
	@echo "$(BLUE)Starting Docker containers...$(RESET)"
	docker-compose -f docker/docker-compose.yml up -d
	@echo "$(GREEN)✓ Docker containers started$(RESET)"

docker-stop: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(RESET)"
	docker-compose -f docker/docker-compose.yml down
	@echo "$(GREEN)✓ Docker containers stopped$(RESET)"

docker-push: docker-build ## Push Docker images to registry
	@echo "$(BLUE)Pushing Docker images...$(RESET)"
	docker tag $(PROJECT_NAME):$(VERSION) $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION)
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME):$(VERSION)
	@echo "$(GREEN)✓ Docker images pushed$(RESET)"

# Database Operations
backup-db: ## Backup database
	@echo "$(BLUE)Creating database backup...$(RESET)"
	@mkdir -p backups
	pg_dump $(DATABASE_URL) > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Database backup created$(RESET)"

migrate-db: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(RESET)"
	$(PYTHON) -m alembic upgrade head
	@echo "$(GREEN)✓ Database migrations completed$(RESET)"

seed-data: ## Seed database with sample data
	@echo "$(BLUE)Seeding database with sample data...$(RESET)"
	$(PYTHON) scripts/seed_data.py
	@echo "$(GREEN)✓ Database seeded$(RESET)"

# Deployment Environments
deploy-local: ## Deploy to local environment
	@echo "$(BLUE)Deploying to local environment...$(RESET)"
	@make install
	@make setup-env
	@make test-fast
	@make dev
	@echo "$(GREEN)✓ Local deployment complete$(RESET)"

deploy-staging: ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging environment...$(RESET)"
	@export ENVIRONMENT=staging
	@make test
	@make lint
	@make security-scan
	@make docker-build
	@make deploy-config
	@make lambda-deploy
	@echo "$(GREEN)✓ Staging deployment complete$(RESET)"

deploy-prod: ## Deploy to production environment
	@echo "$(BLUE)Deploying to production environment...$(RESET)"
	@export ENVIRONMENT=production
	@make test
	@make lint
	@make security-scan
	@make backup-db
	@make docker-build
	@make docker-push
	@make deploy-config
	@make lambda-deploy
	@make setup-monitoring
	@echo "$(GREEN)✓ Production deployment complete$(RESET)"

# Utilities
clean: ## Clean build artifacts and temporary files
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	@echo "$(GREEN)✓ Cleanup completed$(RESET)"

logs: ## View application logs
	@echo "$(BLUE)Viewing application logs...$(RESET)"
	tail -f logs/lcopilot-trust-platform.log || echo "No log file found"

status: ## Show deployment status
	@echo "$(BLUE)Deployment Status$(RESET)"
	@echo "=================="
	@echo "Environment: $(ENV)"
	@echo "Version: $(VERSION)"
	@echo "AWS Region: $(AWS_REGION)"
	@echo ""
	@echo "Local Services:"
	@pgrep -f "python.*app.py" > /dev/null && echo "$(GREEN)✓ SME Portal running$(RESET)" || echo "$(RED)✗ SME Portal stopped$(RESET)"
	@pgrep -f "python.*main.py" > /dev/null && echo "$(GREEN)✓ API server running$(RESET)" || echo "$(RED)✗ API server stopped$(RESET)"
	@redis-cli ping > /dev/null 2>&1 && echo "$(GREEN)✓ Redis running$(RESET)" || echo "$(RED)✗ Redis stopped$(RESET)"

# Demo Commands
demo: ## Run complete demo setup
	@echo "$(BLUE)Setting up demo environment...$(RESET)"
	@make dev-sandbox
	@echo "$(GREEN)✓ Demo environment ready$(RESET)"
	@echo ""
	@echo "$(BLUE)Demo URLs:$(RESET)"
	@echo "  Portal:     http://localhost:5001"
	@echo "  API:        http://localhost:5000"
	@echo "  Health:     http://localhost:5000/health"
	@echo "  Bank Demo:  python3 sme_portal/demo_bank_profiles.py"
	@echo ""

demo-bank-profiles: ## Run bank profiles demo
	@echo "$(BLUE)Running bank profiles demo...$(RESET)"
	cd sme_portal && $(PYTHON) demo_bank_profiles.py
	@echo "$(GREEN)✓ Bank profiles demo completed$(RESET)"

# CI/CD Integration
ci-test: ## Run tests for CI/CD pipeline
	@echo "$(BLUE)Running CI/CD tests...$(RESET)"
	@make install
	@make lint
	@make test
	@make security-scan
	@echo "$(GREEN)✓ CI/CD tests passed$(RESET)"

# Quick actions for development
quick-test: ## Quick test for development
	@echo "$(BLUE)Running quick development tests...$(RESET)"
	$(PYTHON) -m pytest tests/test_textract_fallback.py::test_initialization -v
	$(PYTHON) -m pytest tests/async/test_async_pipeline.py::TestQueueProducer::test_queue_producer_initialization -v
	@echo "$(GREEN)✓ Quick tests passed$(RESET)"

# Installation verification
verify-install: ## Verify installation
	@echo "$(BLUE)Verifying installation...$(RESET)"
	@$(PYTHON) --version
	@$(PIP) --version
	@redis-cli --version || echo "$(YELLOW)Redis not installed$(RESET)"
	@aws --version || echo "$(YELLOW)AWS CLI not installed$(RESET)"
	@docker --version || echo "$(YELLOW)Docker not installed$(RESET)"
	@echo "$(GREEN)✓ Installation verification complete$(RESET)"
#   make setup-prod          # Deploy production environment
#   make verify-all          # Verify both environments
#   make test-staging        # Test staging alarms
#   make ci-checks           # Run CI validation checks

.PHONY: help setup-staging setup-prod verify-staging verify-prod verify-all test-staging test-prod consistency-check ci-checks clean

# Default target
help:
	@echo "🚀 LCopilot Enterprise Observability & Monitoring Automation"
	@echo "============================================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup-staging        Deploy staging monitoring resources"
	@echo "  setup-prod          Deploy production monitoring resources"
	@echo "  setup-all           Deploy both environments"
	@echo "  setup-observability Deploy full observability stack"
	@echo ""
	@echo "Verification Commands:"
	@echo "  verify-staging      Verify staging configuration"
	@echo "  verify-prod         Verify production configuration"
	@echo "  verify-all          Verify both environments"
	@echo "  verify-observability Verify complete observability stack"
	@echo "  consistency-check   Check cross-environment consistency"
	@echo ""
	@echo "Observability Commands:"
	@echo "  deploy-dashboards   Deploy CloudWatch dashboards"
	@echo "  run-canaries        Execute synthetic canaries"
	@echo "  generate-sla-report Generate monthly SLA report"
	@echo "  security-scan-logs  Analyze security events in logs"
	@echo "  test-chaos          Run controlled chaos experiments"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test-staging        Run end-to-end tests for staging"
	@echo "  test-prod           Run end-to-end tests for production"
	@echo "  test-all            Run tests for both environments"
	@echo "  test-observability  Run observability system tests"
	@echo ""
	@echo "CI/CD Commands:"
	@echo "  ci-checks           Run all CI validation checks"
	@echo "  security-scan       Run security scans"
	@echo "  config-validate     Validate enterprise configuration"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  clean               Clean up temporary files"
	@echo "  logs                Show recent CloudWatch logs"
	@echo "  status              Show current system status"

# Environment variables
PYTHON := python3
CONFIG_FILE := config/enterprise_config.json
LOG_LEVEL := INFO

# Check if enterprise config exists
check-config:
	@if [ ! -f $(CONFIG_FILE) ]; then \
		echo "❌ Enterprise config not found: $(CONFIG_FILE)"; \
		echo "   Please create the configuration file first"; \
		exit 1; \
	fi
	@echo "✅ Enterprise config found"

# Validate configuration file
config-validate: check-config
	@echo "🔍 Validating enterprise configuration..."
	@jq empty $(CONFIG_FILE) || (echo "❌ Invalid JSON in config file" && exit 1)
	@echo "✅ Configuration is valid JSON"
	@$(PYTHON) -c "import json; config=json.load(open('$(CONFIG_FILE)')); \
		assert 'environments' in config, 'Missing environments section'; \
		assert 'staging' in config['environments'], 'Missing staging config'; \
		assert 'prod' in config['environments'], 'Missing prod config'; \
		print('✅ Configuration structure is valid')"

# Setup Commands
setup-staging: config-validate
	@echo "🚀 Setting up staging monitoring..."
	@$(PYTHON) setup_alarm.py --env staging
	@echo "✅ Staging setup completed"

setup-prod: config-validate
	@echo "🚀 Setting up production monitoring..."
	@$(PYTHON) setup_alarm.py --env prod
	@echo "✅ Production setup completed"

setup-all: setup-staging setup-prod
	@echo "🎉 All environments set up successfully"

# Verification Commands
verify-staging: check-config
	@echo "🔍 Verifying staging configuration..."
	@$(PYTHON) verify_alarm.py --env staging

verify-prod: check-config
	@echo "🔍 Verifying production configuration..."
	@$(PYTHON) verify_alarm.py --env prod

verify-all: verify-staging verify-prod
	@echo "✅ All environment verifications completed"

consistency-check: check-config
	@echo "🔍 Running cross-environment consistency check..."
	@$(PYTHON) verify_multi_env_consistency.py --verbose

# Testing Commands
test-staging: check-config
	@echo "🧪 Running staging end-to-end tests..."
	@$(PYTHON) cloudwatch_alert_test.py --env staging --count 4
	@echo "✅ Staging tests completed"

test-prod: check-config
	@echo "🧪 Running production end-to-end tests..."
	@echo "⚠️  This will trigger production alarms!"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(PYTHON) cloudwatch_alert_test.py --env prod --count 6
	@echo "✅ Production tests completed"

test-all: test-staging
	@echo "🧪 All tests completed (production tests require manual confirmation)"

# CI/CD Commands
ci-checks: config-validate security-scan
	@echo "🔍 Running CI validation checks..."
	@echo "Checking Python syntax..."
	@$(PYTHON) -m py_compile setup_alarm.py
	@$(PYTHON) -m py_compile verify_alarm.py
	@$(PYTHON) -m py_compile cloudwatch_alert_test.py
	@$(PYTHON) -m py_compile verify_multi_env_consistency.py
	@echo "✅ Python syntax check passed"

	@echo "Checking Lambda code..."
	@$(PYTHON) -m py_compile lambda/escalation_router.py
	@echo "✅ Lambda code check passed"

	@echo "Validating Terraform..."
	@cd terraform && terraform fmt -check=true -diff=true
	@cd terraform && terraform validate
	@echo "✅ Terraform validation passed"

	@echo "Checking CDK code..."
	@cd cdk && $(PYTHON) -m py_compile lcopilot_monitoring_stack.py
	@echo "✅ CDK code check passed"

	@echo "🎉 All CI checks passed"

security-scan:
	@echo "🔒 Running security scans..."
	@echo "Checking for sensitive data in config..."
	@if grep -r "AKIA\|aws_secret_access_key\|password" $(CONFIG_FILE) 2>/dev/null; then \
		echo "❌ Potential sensitive data found in config"; \
		exit 1; \
	fi
	@echo "✅ No sensitive data found in config"

	@echo "Checking for hardcoded secrets in code..."
	@if grep -r "AKIA\|aws_secret_access_key\|password" *.py lambda/*.py 2>/dev/null; then \
		echo "❌ Potential hardcoded secrets found"; \
		exit 1; \
	fi
	@echo "✅ No hardcoded secrets found"

	@echo "✅ Security scan completed"

# Maintenance Commands
status: check-config
	@echo "📊 Current System Status"
	@echo "========================"
	@echo ""
	@echo "Configuration:"
	@echo "  Config file: $(CONFIG_FILE)"
	@echo "  Last modified: $$(stat -f '%Sm' $(CONFIG_FILE) 2>/dev/null || stat -c '%y' $(CONFIG_FILE) 2>/dev/null || echo 'Unknown')"
	@echo ""
	@echo "AWS Resources:"
	@$(PYTHON) verify_multi_env_consistency.py --env both 2>/dev/null || echo "  Run 'make verify-all' for detailed status"
	@echo ""
	@echo "Recent Activity:"
	@echo "  Check CloudWatch console for recent alarm activity"

logs:
	@echo "📋 Recent CloudWatch Logs"
	@echo "========================="
	@echo "Use AWS CLI or Console to view logs:"
	@echo "  aws logs tail /aws/lambda/lcopilot-staging --follow"
	@echo "  aws logs tail /aws/lambda/lcopilot-prod --follow"

clean:
	@echo "🧹 Cleaning up temporary files..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.zip" -delete 2>/dev/null || true
	@rm -f terraform/*.tfplan 2>/dev/null || true
	@rm -f terraform/plan_output.txt 2>/dev/null || true
	@rm -f cdk/cdk.out 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Development helpers
dev-setup:
	@echo "🛠️  Setting up development environment..."
	@pip install boto3 python-dotenv requests jq
	@echo "✅ Development dependencies installed"

fmt:
	@echo "🎨 Formatting code..."
	@$(PYTHON) -m black *.py lambda/*.py 2>/dev/null || echo "Install 'black' for code formatting: pip install black"
	@cd terraform && terraform fmt
	@echo "✅ Code formatting completed"

# Environment-specific shortcuts
staging: setup-staging verify-staging
	@echo "🎯 Staging environment ready"

prod: setup-prod verify-prod
	@echo "🎯 Production environment ready"

# Emergency procedures
emergency-disable-staging:
	@echo "🚨 Emergency: Disabling staging alarms..."
	@aws cloudwatch disable-alarm-actions --alarm-names lcopilot-error-spike-staging 2>/dev/null || echo "❌ Failed to disable staging alarms"

emergency-disable-prod:
	@echo "🚨 Emergency: Disabling production alarms..."
	@echo "⚠️  This will disable PRODUCTION monitoring!"
	@read -p "Are you sure? Type 'DISABLE' to continue: " confirm && [ "$$confirm" = "DISABLE" ] || exit 1
	@aws cloudwatch disable-alarm-actions --alarm-names lcopilot-error-spike-prod 2>/dev/null || echo "❌ Failed to disable production alarms"

# Documentation
docs:
	@echo "📚 Available Documentation:"
	@echo "  - MULTI_ENV_ALARM_GUIDE.md - Multi-environment setup guide"
	@echo "  - ENTERPRISE_MONITORING_PLAYBOOK.md - Enterprise playbook (when available)"
	@echo "  - config/enterprise_config.json - Configuration reference"
	@echo "  - README.md - Project overview"

# Observability Commands
setup-observability: setup-all deploy-dashboards
	@echo "🎉 Full observability stack deployment completed"

deploy-dashboards:
	@echo "📊 Deploying CloudWatch dashboards..."
	@$(PYTHON) utils/dashboard_manager.py --env staging --deploy
	@$(PYTHON) utils/dashboard_manager.py --env prod --deploy
	@echo "✅ Dashboards deployed to both environments"

verify-observability: check-config
	@echo "🔍 Running comprehensive observability verification..."
	@$(PYTHON) verify_observability_stack.py --env both --verbose

run-canaries:
	@echo "🧪 Running synthetic canaries..."
	@$(PYTHON) canaries/golden_path_canary.py --env staging --scenario all --publish-metrics
	@echo "✅ Canaries completed for staging"

generate-sla-report:
	@echo "📊 Generating monthly SLA report..."
	@read -p "Enter report month (YYYY-MM): " month && \
	$(PYTHON) slo_reporting/sla_report_generator.py --env prod --month $$month --format html --output "sla-report-prod-$$month.html"
	@echo "✅ SLA report generated"

security-scan-logs:
	@echo "🔒 Analyzing security events..."
	@$(PYTHON) security/security_monitor.py --env prod --analyze-logs --hours 24 --output security-analysis.json
	@echo "✅ Security analysis completed"

test-chaos:
	@echo "🌪️ Testing chaos engineering (staging only)..."
	@echo "⚠️ This will inject controlled faults for testing"
	@read -p "Continue with chaos test? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(PYTHON) chaos/chaos_controller.py --env staging --fault error_spike --duration 60
	@echo "✅ Chaos test completed"

test-observability: verify-observability run-canaries
	@echo "🧪 Running comprehensive observability tests..."
	@echo "✅ All observability tests completed"

# Enhanced log analysis
logs-insights:
	@echo "📋 Running CloudWatch Logs Insights queries..."
	@$(PYTHON) utils/log_insights_manager.py --env prod --query TopErrorTypes
	@$(PYTHON) utils/log_insights_manager.py --env prod --query ErrorFrequency

show-dashboard-urls:
	@echo "📊 CloudWatch Dashboard URLs:"
	@echo "  Staging: https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1#dashboards:name=lcopilot-health-staging"
	@echo "  Production: https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1#dashboards:name=lcopilot-health-prod"

# ========================================
# Regression Testing (Phase 4.5)
# ========================================

.PHONY: test-regression test-regression-html test-regression-security test-regression-rate-limiting test-regression-integration

test-regression:
	@echo "🧪 Running comprehensive regression tests..."
	@$(PYTHON) -m pytest tests/regression/ -v --tb=short --color=yes
	@echo "✅ Regression tests completed"

test-regression-html:
	@echo "🧪 Running regression tests with HTML report..."
	@mkdir -p test-results/html
	@$(PYTHON) -m pytest tests/regression/ -v --html=test-results/html/regression-report.html --self-contained-html --cov=. --cov-report=html:test-results/html/coverage
	@echo "✅ Regression tests completed. Report: test-results/html/regression-report.html"

test-regression-security:
	@echo "🔒 Running security regression tests..."
	@$(PYTHON) -m pytest tests/regression/test_security.py -v --tb=short
	@echo "✅ Security tests completed"

test-regression-rate-limiting:
	@echo "⚡ Running rate limiting regression tests..."
	@$(PYTHON) -m pytest tests/regression/test_rate_limiting.py -v --tb=short
	@echo "✅ Rate limiting tests completed"

test-regression-integration:
	@echo "🔄 Running integration regression tests..."
	@$(PYTHON) -m pytest tests/regression/test_integration_flow.py -v --tb=short
	@echo "✅ Integration tests completed"

test-regression-parallel:
	@echo "🚀 Running regression tests in parallel..."
	@$(PYTHON) -m pytest tests/regression/ -n auto -v --tb=short
	@echo "✅ Parallel regression tests completed"

clean-test-artifacts:
	@echo "🧹 Cleaning test artifacts..."
	@rm -rf test-results/ htmlcov/ .pytest_cache/ .coverage
	@echo "✅ Test artifacts cleaned"

# CI target for GitHub Actions
ci: ci-checks consistency-check verify-observability test-regression
	@echo "🎉 CI pipeline completed successfully"