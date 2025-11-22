# TRDR Hub Bank Pilot Makefile
# Commands for managing bank pilot infrastructure, deployments, and compliance operations

.PHONY: help bank_init bank_promote_uat bank_promote_prod bank_bundle_evidence bank_dashboards bank_test bank_deploy db_init migrate upgrade downgrade seed_demo pilot_demo admin_demo backup restore dr_drill rotate_secrets runbooks_serve audit-rules

# Variables
BANK_ALIAS ?= demo
ENVIRONMENT ?= sandbox
KUBECTL_CONTEXT ?= trdrhub-bank-pilot
HELM_NAMESPACE ?= trdrhub-system

# Default target
help: ## Show this help message
	@echo "TRDR Hub Bank Pilot Management"
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# Bank Pilot Management Commands
bank_init: ## Initialize bank tenant (Usage: make bank_init BANK_ALIAS=jpmorgan)
	@echo "🏦 Initializing bank tenant: $(BANK_ALIAS)"
	@if [ "$(BANK_ALIAS)" = "demo" ]; then \
		echo "⚠️  Using demo alias - this will create a demo tenant"; \
	fi
	kubectl apply -f infra/k8s/tenants/bank-$(BANK_ALIAS)/namespace.yaml
	kubectl apply -f infra/k8s/tenants/bank-$(BANK_ALIAS)/networkpolicy.yaml
	kubectl apply -f infra/k8s/tenants/bank-$(BANK_ALIAS)/secrets.yaml
	@echo "✅ Bank tenant $(BANK_ALIAS) infrastructure created"
	@echo "🚀 Provisioning sandbox environment..."
	kubectl apply -k infra/k8s/envs/sandbox/bank-$(BANK_ALIAS)/
	@echo "✅ Sandbox environment ready for $(BANK_ALIAS)"

bank_promote_uat: ## Promote bank tenant to UAT (Usage: make bank_promote_uat BANK_ALIAS=jpmorgan)
	@echo "🔄 Promoting $(BANK_ALIAS) to UAT environment"
	@echo "📋 Running UAT promotion checks..."
	python scripts/bank_pilot/promote_to_uat.py --bank-alias $(BANK_ALIAS) --check-only
	@read -p "Checks passed. Continue with UAT promotion? [y/N] " confirm && [ "$$confirm" = "y" ]
	python scripts/bank_pilot/promote_to_uat.py --bank-alias $(BANK_ALIAS) --execute
	kubectl apply -k infra/k8s/envs/uat/bank-$(BANK_ALIAS)/
	@echo "✅ $(BANK_ALIAS) promoted to UAT"

bank_promote_prod: ## Promote bank tenant to Production (Usage: make bank_promote_prod BANK_ALIAS=jpmorgan)
	@echo "🚨 PRODUCTION PROMOTION: $(BANK_ALIAS)"
	@echo "📋 Running production readiness checks..."
	python scripts/bank_pilot/promote_to_prod.py --bank-alias $(BANK_ALIAS) --check-only
	@read -p "⚠️  This will enable billing and deploy to production. Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	@read -p "Enter approver email: " approver_email && \
	python scripts/bank_pilot/promote_to_prod.py --bank-alias $(BANK_ALIAS) --approver "$$approver_email" --execute
	kubectl apply -k infra/k8s/envs/prod/bank-$(BANK_ALIAS)/
	@echo "✅ $(BANK_ALIAS) promoted to PRODUCTION with billing enabled"

bank_bundle_evidence: ## Generate regulatory evidence bundle (Usage: make bank_bundle_evidence BANK_ALIAS=jpmorgan)
	@echo "📊 Generating regulatory evidence bundle for $(BANK_ALIAS)"
	mkdir -p evidence/$(BANK_ALIAS)
	python scripts/bank_pilot/generate_pilot_evidence_bundle.py \
		--bank-alias $(BANK_ALIAS) \
		--output evidence/$(BANK_ALIAS)/bank-$(BANK_ALIAS)-evidence-$(shell date +%Y%m).zip
	@echo "✅ Evidence bundle created: evidence/$(BANK_ALIAS)/bank-$(BANK_ALIAS)-evidence-$(shell date +%Y%m).zip"

bank_dashboards: ## Provision bank-specific Grafana dashboards (Usage: make bank_dashboards BANK_ALIAS=jpmorgan)
	@echo "📈 Provisioning Grafana dashboards for $(BANK_ALIAS)"
	kubectl create configmap bank-$(BANK_ALIAS)-dashboards \
		--from-file=ops/grafana/dashboards/bank/ \
		--namespace=$(HELM_NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl label configmap bank-$(BANK_ALIAS)-dashboards \
		grafana_dashboard=1 \
		tenant=$(BANK_ALIAS) \
		--namespace=$(HELM_NAMESPACE)
	@echo "✅ Dashboards provisioned for $(BANK_ALIAS)"

# Workflow Features Dashboards
deploy_workflow_dashboards: ## Deploy workflow monitoring dashboards
	@echo "📊 Deploying workflow monitoring dashboards"
	kubectl create configmap workflow-dashboards \
		--from-file=ops/grafana/dashboards/workflows/ \
		--namespace=$(HELM_NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl label configmap workflow-dashboards \
		grafana_dashboard=1 \
		component=workflows \
		--namespace=$(HELM_NAMESPACE)
	@echo "✅ Workflow dashboards deployed"

deploy_prometheus_rules: ## Deploy Prometheus alerting rules for workflows
	@echo "⚠️  Deploying Prometheus alerting rules"
	kubectl create configmap workflow-alert-rules \
		--from-file=prom_rules/workflow.yml \
		--namespace=$(HELM_NAMESPACE) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl label configmap workflow-alert-rules \
		prometheus_rule=1 \
		component=workflows \
		--namespace=$(HELM_NAMESPACE)
	@echo "✅ Prometheus rules deployed"

setup_monitoring: ## Setup complete monitoring stack for workflows
	@echo "🎯 Setting up complete workflow monitoring stack"
	make deploy_workflow_dashboards
	make deploy_prometheus_rules
	@echo "✅ Workflow monitoring stack ready"

# Development and Testing
bank_test: ## Run bank pilot test suite
	@echo "🧪 Running bank pilot test suite"
	pytest tests/bank_pilot/ -v --cov=app.routers.bankpilot --cov=app.core.bankpilot
	@echo "✅ Bank pilot tests completed"

bank_test_e2e: ## Run end-to-end bank pilot tests
	@echo "🎭 Running E2E bank pilot tests"
	playwright test tests/bank_pilot/e2e_bank_pilot.spec.ts
	@echo "✅ E2E tests completed"

# Workflow Features Testing
test_workflows: ## Run comprehensive workflow features test suite
	@echo "🔄 Running workflow features test suite"
	pytest tests/workflows/ -v --cov=app.services --cov=app.core --cov=app.routers
	@echo "✅ Workflow features tests completed"

test_notifications: ## Run notification system tests
	@echo "🔔 Running notification system tests"
	pytest tests/workflows/test_notification_service.py tests/api/test_notifications_api.py -v
	@echo "✅ Notification tests completed"

test_exports: ## Run export/reporting tests
	@echo "📊 Running export and reporting tests"
	pytest tests/workflows/test_export_service.py tests/api/test_reports_api.py -v
	@echo "✅ Export tests completed"

test_governance: ## Run governance hooks tests
	@echo "🔐 Running governance and approval tests"
	pytest tests/workflows/test_governance_hooks.py -v
	@echo "✅ Governance tests completed"

test_metrics: ## Run observability and metrics tests
	@echo "📈 Running metrics and observability tests"
	pytest tests/workflows/test_workflow_metrics.py -v
	@echo "✅ Metrics tests completed"

test_events: ## Run event system tests
	@echo "⚡ Running event system tests"
	pytest tests/workflows/test_events.py -v
	@echo "✅ Event system tests completed"

# Infrastructure Management
bank_deploy_gateway: ## Deploy enterprise security gateway
	@echo "🛡️  Deploying enterprise security gateway"
	helm upgrade --install enterprise-gateway infra/helm/enterprise-gateway/ \
		--namespace $(HELM_NAMESPACE) \
		--create-namespace \
		--values infra/helm/enterprise-gateway/values.yaml
	@echo "✅ Enterprise gateway deployed"

bank_update_gateway: ## Update gateway configuration for specific bank
	@echo "🔧 Updating gateway configuration for $(BANK_ALIAS)"
	helm upgrade enterprise-gateway infra/helm/enterprise-gateway/ \
		--namespace $(HELM_NAMESPACE) \
		--set bankPilot.tenants[0].alias=$(BANK_ALIAS) \
		--reuse-values
	@echo "✅ Gateway updated for $(BANK_ALIAS)"

# Monitoring and Troubleshooting
bank_status: ## Check bank tenant status (Usage: make bank_status BANK_ALIAS=jpmorgan)
	@echo "📊 Status for bank tenant: $(BANK_ALIAS)"
	@echo "=== Namespace Status ==="
	kubectl get ns | grep bank-$(BANK_ALIAS) || echo "❌ Namespace not found"
	@echo "=== Pod Status ==="
	kubectl get pods -n bank-$(BANK_ALIAS) 2>/dev/null || echo "❌ No pods found"
	@echo "=== Service Status ==="
	kubectl get svc -n bank-$(BANK_ALIAS) 2>/dev/null || echo "❌ No services found"
	@echo "=== Ingress Status ==="
	kubectl get ingress -n bank-$(BANK_ALIAS) 2>/dev/null || echo "❌ No ingress found"

bank_logs: ## Get logs for bank tenant (Usage: make bank_logs BANK_ALIAS=jpmorgan)
	@echo "📝 Fetching logs for $(BANK_ALIAS)"
	kubectl logs -n bank-$(BANK_ALIAS) -l app.kubernetes.io/instance=bank-$(BANK_ALIAS) --tail=100

bank_shell: ## Get shell access to bank tenant pod (Usage: make bank_shell BANK_ALIAS=jpmorgan)
	kubectl exec -it -n bank-$(BANK_ALIAS) \
		$$(kubectl get pods -n bank-$(BANK_ALIAS) -l app.kubernetes.io/name=trdrhub -o jsonpath='{.items[0].metadata.name}') \
		-- /bin/bash

# Data Management
bank_backup: ## Create backup for bank tenant (Usage: make bank_backup BANK_ALIAS=jpmorgan)
	@echo "💾 Creating backup for $(BANK_ALIAS)"
	kubectl create job bank-$(BANK_ALIAS)-backup-$(shell date +%Y%m%d-%H%M%S) \
		--from=cronjob/bank-$(BANK_ALIAS)-backup -n bank-$(BANK_ALIAS)
	@echo "✅ Backup job created for $(BANK_ALIAS)"

bank_restore: ## Restore bank tenant from backup (Usage: make bank_restore BANK_ALIAS=jpmorgan BACKUP_ID=20240115-120000)
	@echo "🔄 Restoring $(BANK_ALIAS) from backup $(BACKUP_ID)"
	@read -p "⚠️  This will restore data from backup. Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	kubectl create job bank-$(BANK_ALIAS)-restore-$(shell date +%Y%m%d-%H%M%S) \
		--from=cronjob/bank-$(BANK_ALIAS)-restore -n bank-$(BANK_ALIAS) \
		-- --backup-id $(BACKUP_ID)
	@echo "✅ Restore job created for $(BANK_ALIAS)"

# Security and Compliance
bank_security_scan: ## Run security scan for bank tenant (Usage: make bank_security_scan BANK_ALIAS=jpmorgan)
	@echo "🔍 Running security scan for $(BANK_ALIAS)"
	kubectl run security-scan-$(BANK_ALIAS) \
		--image=aquasec/trivy:latest \
		--rm -i --restart=Never \
		-- image trdrhub-api:latest
	@echo "✅ Security scan completed for $(BANK_ALIAS)"

bank_compliance_check: ## Run compliance checks for bank tenant (Usage: make bank_compliance_check BANK_ALIAS=jpmorgan)
	@echo "✅ Running compliance checks for $(BANK_ALIAS)"
	python scripts/bank_pilot/compliance_checker.py --bank-alias $(BANK_ALIAS) --report
	@echo "✅ Compliance check completed for $(BANK_ALIAS)"

# Cleanup
bank_cleanup: ## Remove bank tenant (Usage: make bank_cleanup BANK_ALIAS=jpmorgan)
	@echo "🗑️  WARNING: This will completely remove $(BANK_ALIAS) tenant"
	@read -p "Are you sure? This action cannot be undone. Type '$(BANK_ALIAS)' to confirm: " confirm && [ "$$confirm" = "$(BANK_ALIAS)" ]
	kubectl delete namespace bank-$(BANK_ALIAS) --ignore-not-found
	kubectl delete -k infra/k8s/envs/sandbox/bank-$(BANK_ALIAS)/ --ignore-not-found
	kubectl delete -k infra/k8s/envs/uat/bank-$(BANK_ALIAS)/ --ignore-not-found
	kubectl delete -k infra/k8s/envs/prod/bank-$(BANK_ALIAS)/ --ignore-not-found
	@echo "✅ Bank tenant $(BANK_ALIAS) removed"

# CI/CD Integration
ci_test: ## Run all tests for CI/CD pipeline
	@echo "🤖 Running CI test suite"
	make bank_test
	make bank_test_e2e
	make test_workflows
	@echo "✅ All CI tests passed"

ci_test_unit: ## Run unit tests only (faster CI option)
	@echo "⚡ Running unit tests"
	pytest tests/workflows/ tests/bank_pilot/ -v --tb=short
	@echo "✅ Unit tests passed"

ci_deploy: ## Deploy bank pilot infrastructure (CI/CD)
	@echo "🚀 Deploying bank pilot infrastructure"
	make bank_deploy_gateway
	make setup_monitoring
	@echo "✅ Bank pilot infrastructure deployed"

ci_security: ## Run security checks (CI/CD)
	@echo "🔒 Running security checks"
	# Run security linting
	bandit -r app/ -f json -o security-report.json
	# Run dependency scanning
	safety check --json --output safety-report.json
	# Check for hardcoded secrets
	detect-secrets scan --all-files --baseline .secrets.baseline
	@echo "✅ Security checks completed"

ci_lint: ## Run code quality checks
	@echo "✨ Running code quality checks"
	flake8 app/ tests/ --statistics
	black app/ tests/ --check
	isort app/ tests/ --check-only
	mypy app/
	@echo "✅ Code quality checks passed"

# Documentation
bank_docs: ## Generate bank pilot documentation
	@echo "📚 Generating bank pilot documentation"
	mkdir -p docs/generated
	python scripts/generate_api_docs.py --module bankpilot --output docs/generated/bank-pilot-api.md
	@echo "✅ Documentation generated"

# Development
dev_setup: ## Setup development environment for bank pilot
	@echo "🛠️  Setting up development environment"
	pip install -r requirements-dev.txt
	pre-commit install
	npm install
	@echo "✅ Development environment ready"

dev_run: ## Run development server with bank pilot features
	@echo "🏃 Starting development server"
	uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

dev_run_with_workers: ## Run development server with background workers
	@echo "🏃 Starting development server with workers"
	# Start Redis if not running
	redis-server --daemonize yes --port 6379 || echo "Redis already running"
	# Start Celery worker in background
	celery -A app.workers worker --loglevel=info --detach
	# Start FastAPI server
	uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

dev_stop_workers: ## Stop background workers
	@echo "🛑 Stopping background workers"
	pkill -f "celery.*worker" || echo "No workers to stop"
	redis-cli shutdown || echo "Redis not running"

# Workflow Feature Development
dev_test_notifications: ## Test notification system in development
	@echo "🔔 Testing notifications in development"
	python -m pytest tests/workflows/test_notification_service.py -v -s
	@echo "✅ Notification tests completed"

dev_test_exports: ## Test export system in development
	@echo "📊 Testing exports in development"
	python -m pytest tests/workflows/test_export_service.py -v -s
	@echo "✅ Export tests completed"

dev_seed_data: ## Seed development database with test data
	@echo "🌱 Seeding development database"
	python scripts/dev/seed_workflow_data.py
	@echo "✅ Development data seeded"

# Quick commands for common scenarios
demo: ## Setup demo bank tenant quickly
	make bank_init BANK_ALIAS=demo
	make bank_dashboards BANK_ALIAS=demo
	@echo "✅ Demo bank tenant ready at: https://demo.enterprise.trdrhub.com"

jpmorgan: ## Setup JPMorgan pilot (example)
	make bank_init BANK_ALIAS=jpmorgan
	make bank_dashboards BANK_ALIAS=jpmorgan
	@echo "✅ JPMorgan pilot ready at: https://jpmorgan.enterprise.trdrhub.com"

# Database Migration Management
db_init: ## Initialize Alembic and create database
	@echo "🗄️  Initializing database with Alembic"
	alembic stamp head
	@echo "✅ Database initialized"

migrate: ## Create new Alembic migration (Usage: make migrate msg="description")
	@echo "📝 Creating new migration: $(msg)"
	alembic revision --autogenerate -m "$(msg)"
	@echo "✅ Migration created"

upgrade: ## Apply database migrations
	@echo "⬆️  Applying database migrations"
	alembic upgrade head
	@echo "✅ Database upgraded"

downgrade: ## Rollback last migration
	@echo "⬇️  Rolling back last migration"
	alembic downgrade -1
	@echo "✅ Database downgraded"

# Demo Data and Pilot Setup
seed_demo: ## Seed database with demo data
	@echo "🌱 Seeding demo data"
	python3 scripts/demo/seed_demo_data.py
	@echo "✅ Demo data seeded"

pilot_demo: db_init upgrade seed_demo ## Setup complete pilot demo environment
	@echo "🚀 TRDR Hub Pilot Demo Ready!"
	@echo "📊 Admin Console: http://localhost:3000/admin"
	@echo "📈 Grafana: http://localhost:3001"
	@echo "🔍 Demo Logins:"
	@echo "  SME Admin: sme.admin@demo.com / sme123"
	@echo "  Bank Officer: bank.officer@demo.com / bank123"
	@echo "  Auditor: auditor@demo.com / audit123"
	@echo "  Super Admin: admin@lcopilot.com / admin123"

admin_demo: ## Open admin console with demo credentials
	@echo "🔐 Demo admin credentials:"
	@echo "  Super Admin: admin@lcopilot.com / admin123"
	@echo "  Bank Officer: bank.officer@demo.com / bank123"
	@echo "  Auditor: auditor@demo.com / audit123"
	open http://localhost:3000/admin

# Disaster Recovery Operations
backup: ## Create full backup (database + objects)
	@echo "💾 Creating full backup"
	python3 scripts/dr/backup_db.py
	python3 scripts/dr/backup_objects.py
	@echo "✅ Full backup completed"

restore: ## Restore from backup (Usage: make restore BACKUP_ID=backup_id)
	@echo "🔄 Restoring from backup: $(BACKUP_ID)"
	python3 scripts/dr/restore_db.py $(BACKUP_ID)
	python3 scripts/dr/restore_objects.py $(BACKUP_ID)
	@echo "✅ Restore completed"

dr_drill: ## Run disaster recovery drill
	@echo "🚨 Running DR drill"
	python3 scripts/dr/dr_drill.py --target-rpo=15 --target-rto=60
	@echo "✅ DR drill completed"

# Secrets Management
rotate_secrets: ## Rotate all application secrets
	@echo "🔐 Rotating application secrets"
	python3 scripts/secrets/rotate_secrets.py --backend=local
	@echo "✅ Secrets rotated"

# Documentation
runbooks_serve: ## Serve operational runbooks locally
	@echo "📚 Starting runbook server"
	cd docs && python3 -m http.server 8080
	@echo "📖 Runbooks available at: http://localhost:8080/runbooks/"

# Ruleset Management
audit-rules: ## Run ruleset integrity audit (validates JSON files and DB state)
	@echo "🔍 Running ruleset integrity audit..."
	@PYTHONPATH=. python apps/api/scripts/recheck_rules.py
	@echo "✅ Ruleset audit completed"

# Version and build info
version: ## Show version information
	@echo "TRDR Hub Bank Pilot"
	@echo "Version: $(shell git describe --tags --always)"
	@echo "Build: $(shell git rev-parse --short HEAD)"
	@echo "Date: $(shell date -u +%Y-%m-%dT%H:%M:%SZ)"