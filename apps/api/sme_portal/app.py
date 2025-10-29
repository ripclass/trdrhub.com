#!/usr/bin/env python3
"""
SME Portal for LCopilot Trust Platform
Minimal web interface for small-to-medium enterprises to access LC compliance validation.
"""

import os
import json
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import secrets
import logging
import time
import yaml
from functools import wraps
from typing import Dict, Any, Optional

# Add trust platform to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from trust_platform.compliance.compliance_integration import ComplianceIntegration
from trust_platform.output.output_layer import OutputLayer
from trust_platform.evidence.evidence_packager import EvidencePackager
from trust_platform.tiers.tier_manager import TierManager
from trust_platform.logging.structured_logger import get_logger
from pipeline.safe_validator import SafeRuleValidator
from bank_simulator import BankModeSimulator
from trust_platform.compliance.bank_profile_engine import BankProfileEngine
from async.api_integration import async_bp, init_async_components

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(16))
app.config['TRUST_CONFIG_PATH'] = str(Path(__file__).parent.parent / 'trust_config.yaml')

# Security: Set maximum file upload size to 10MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max

# Register async processing blueprint
app.register_blueprint(async_bp)

# Initialize async components
try:
    init_async_components(app)
except Exception as e:
    app.logger.warning(f"Failed to initialize async components: {e}")

# Configure logging
app.logger.setLevel(logging.INFO)
structured_logger = get_logger("sme_portal", "development" if os.environ.get('FLASK_ENV') == 'development' else "production")
safe_validator = SafeRuleValidator(structured_logger.logger)

# Initialize services with error handling
try:
    compliance_integration = ComplianceIntegration()
    structured_logger.info("Compliance integration initialized successfully")
except Exception as e:
    structured_logger.error(f"Could not initialize compliance integration: {str(e)}")
    structured_logger.info("Running in demo mode with mock compliance results")
    compliance_integration = None

output_layer = OutputLayer()
evidence_packager = EvidencePackager()
tier_manager = TierManager()

# Initialize Bank-Mode Simulator
try:
    bank_simulator = BankModeSimulator()
    structured_logger.info("Bank-Mode Simulator initialized successfully")
except Exception as e:
    structured_logger.error(f"Could not initialize bank simulator: {str(e)}")
    bank_simulator = None

# Initialize Bank Profile Engine
try:
    bank_profile_engine = BankProfileEngine()
    structured_logger.info("Bank Profile Engine initialized successfully")
except Exception as e:
    structured_logger.error(f"Could not initialize bank profile engine: {str(e)}")
    bank_profile_engine = None

# Load branding configuration
def load_branding_config():
    """Load branding configuration from trust_config.yaml"""
    try:
        config_path = app.config.get('TRUST_CONFIG_PATH')
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                frontend_config = config.get('frontend', {}).get('sme_portal', {})
                branding_config = frontend_config.get('branding', {}).get('default', {})

                # Check for enterprise override
                override_config = frontend_config.get('branding', {}).get('enterprise_override', {})
                if override_config.get('enabled', False):
                    branding_config.update({
                        k: v for k, v in override_config.items()
                        if k != 'enabled' and v
                    })

                return branding_config
    except Exception as e:
        app.logger.warning(f"Failed to load branding config: {e}")

    return {
        'company_name': 'LCopilot',
        'primary_color': '#3b82f6',
        'secondary_color': '#1e293b',
        'tagline': 'Trust Platform for Trade Finance'
    }

branding_config = load_branding_config()

# Make branding available to all templates
@app.context_processor
def inject_branding():
    return {'branding': branding_config}

def convert_bank_result_to_standard(bank_result, tier):
    """Convert bank simulator result to standard compliance result format"""
    if bank_result.get('error'):
        return {
            "compliance_score": 0.0,
            "overall_status": "validation_error",
            "tier_used": tier,
            "validated_rules": [],
            "execution_time_ms": 0,
            "upsell_triggered": False,
            "bank_simulation": bank_result
        }

    # Map bank status to standard status
    status_mapping = {
        'approved': 'compliant',
        'conditional_approval': 'compliant',
        'requires_review': 'issues_found',
        'rejected': 'non_compliant'
    }

    standard_status = status_mapping.get(bank_result.get('overall_status', 'unknown'), 'issues_found')

    # Convert bank validation results to standard rules format
    validated_rules = []
    for validation in bank_result.get('validation_results', []):
        rule = {
            "id": validation.get('rule_id', 'BANK-RULE'),
            "description": validation.get('description', ''),
            "status": "pass" if validation.get('status') == 'pass' else "fail",
            "details": "; ".join(validation.get('issues', []) + validation.get('notes', [])),
            "field_location": "bank_specific",
            "suggested_fix": None,
            "bank_specific": validation.get('bank_specific', True)
        }
        validated_rules.append(rule)

    return {
        "compliance_score": bank_result.get('compliance_score', 0.0),
        "overall_status": standard_status,
        "tier_used": tier,
        "validated_rules": validated_rules,
        "execution_time_ms": bank_result.get('simulation_metadata', {}).get('simulated_processing_time_ms', 0),
        "upsell_triggered": False,
        "bank_simulation": bank_result
    }

def mock_compliance_validation(lc_document, customer_id, tier):
    """Mock compliance validation for demo mode"""
    return {
        "compliance_score": 0.85,
        "overall_status": "compliant",
        "tier_used": tier,
        "validated_rules": [
            {
                "id": "UCP600-6",
                "description": "LC expiry date validation",
                "status": "pass",
                "details": "Expiry date is valid and allows sufficient time for shipment",
                "field_location": "expiry_date",
                "suggested_fix": None
            },
            {
                "id": "BD-002",
                "description": "Currency consistency for Bangladesh imports",
                "status": "fail",
                "details": "EUR currency detected instead of standard USD",
                "field_location": "amount.currency",
                "suggested_fix": "Change currency to USD for Bangladesh compliance"
            }
        ],
        "execution_time_ms": 125,
        "upsell_triggered": False
    }

@app.route('/')
def dashboard():
    """Main dashboard for SME users"""
    customer_id = session.get('customer_id', 'demo-user')
    tier = request.args.get('tier', 'free')

    # Get customer summary
    customer_summary = tier_manager.get_customer_summary(customer_id, tier)

    return render_template('dashboard.html',
                         customer_summary=customer_summary,
                         tier=tier)

@app.route('/validate', methods=['GET', 'POST'])
def validate_lc():
    """LC validation interface"""
    if request.method == 'GET':
        # Get bank categories for dropdown
        bank_categories = {}
        if bank_profile_engine:
            bank_categories = bank_profile_engine.get_banks_for_dropdown()

        # Check if async processing is enabled
        async_enabled = False
        try:
            config_path = app.config.get('TRUST_CONFIG_PATH')
            if config_path and os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    async_enabled = config.get('async_processing', {}).get('enabled', False)
        except Exception:
            pass

        return render_template('validate.html',
                             bank_categories=bank_categories,
                             async_enabled=async_enabled)

    try:
        customer_id = session.get('customer_id', 'demo-user')
        tier = request.form.get('tier', 'free')
        bank_mode = request.form.get('bank_mode', '')

        # Handle file upload or JSON input
        lc_data = None
        original_filename = None

        if 'lc_file' in request.files and request.files['lc_file'].filename:
            # File upload
            file = request.files['lc_file']
            original_filename = file.filename

            # Security: Explicit file size check
            # Read the content to check size
            file_content = file.read()
            file_size = len(file_content)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

            if file_size > MAX_FILE_SIZE:
                flash(f'File too large. Maximum size is 10MB, your file is {file_size / (1024*1024):.1f}MB', 'error')
                return redirect(url_for('validate_lc'))

            # Reset file pointer for reading
            file.seek(0)

            if file.filename.endswith('.json'):
                lc_data = json.load(file.stream)
            else:
                flash('Please upload a JSON file containing LC data', 'error')
                return redirect(url_for('validate_lc'))

        elif request.form.get('lc_json'):
            # Direct JSON input
            try:
                lc_data = json.loads(request.form.get('lc_json'))
            except json.JSONDecodeError:
                flash('Invalid JSON format in LC data', 'error')
                return redirect(url_for('validate_lc'))
        else:
            flash('Please provide LC data either as a file upload or JSON input', 'error')
            return redirect(url_for('validate_lc'))

        # Store in session for later use (evidence packs)
        session['last_lc_data'] = lc_data
        session['last_lc_filename'] = original_filename or 'lc_document.json'
        session['last_bank_mode'] = bank_mode

        # Validate LC compliance
        if bank_mode and bank_simulator:
            # Use bank-specific validation with legacy simulator
            result = bank_simulator.validate_with_bank(lc_data, bank_mode)
            # Convert bank simulator result to standard format
            result = convert_bank_result_to_standard(result, tier)
        elif bank_mode and bank_profile_engine:
            # Use new bank profile engine for enforcement
            if compliance_integration:
                result = compliance_integration.validate_lc_compliance(
                    lc_document=lc_data,
                    customer_id=customer_id,
                    tier=tier
                )
            else:
                result = mock_compliance_validation(lc_data, customer_id, tier)

            # Apply bank-specific enforcement profile
            result = bank_profile_engine.apply_bank_profile(result, bank_mode)
        elif compliance_integration:
            result = compliance_integration.validate_lc_compliance(
                lc_document=lc_data,
                customer_id=customer_id,
                tier=tier
            )
        else:
            # Use mock validation for demo
            result = mock_compliance_validation(lc_data, customer_id, tier)

        # Store result in session
        session['last_validation_result'] = result

        # Generate user-friendly output
        if result.get('overall_status') == 'blocked':
            # Tier-gated response
            return render_template('validation_blocked.html',
                                 result=result,
                                 tier=tier,
                                 lc_number=lc_data.get('lc_number', 'Unknown'))

        # Generate plain English summary
        plain_english = output_layer.to_plain_english(result)

        return render_template('validation_result.html',
                             result=result,
                             plain_english=plain_english,
                             tier=tier,
                             lc_number=lc_data.get('lc_number', 'Unknown'))

    except Exception as e:
        app.logger.error(f"Validation error: {str(e)}")
        app.logger.error(traceback.format_exc())
        flash(f'Validation failed: {str(e)}', 'error')
        return redirect(url_for('validate_lc'))

@app.route('/evidence-pack')
def create_evidence_pack():
    """Create evidence pack from last validation"""
    if 'last_validation_result' not in session or 'last_lc_data' not in session:
        flash('No recent validation found. Please validate an LC first.', 'error')
        return redirect(url_for('validate_lc'))

    try:
        customer_id = session.get('customer_id', 'demo-user')
        tier = request.args.get('tier', 'free')

        # Check if tier supports evidence packs
        tier_info = tier_manager.get_tier_info(tier)
        if not tier_info.evidence_packs:
            return render_template('feature_not_available.html',
                                 feature='Evidence Packs',
                                 tier=tier_info.name,
                                 required_tier='Professional')

        # Create evidence package
        package_path, package_hash = evidence_packager.create_evidence_pack(
            compliance_result=session['last_validation_result'],
            lc_document=session['last_lc_data'],
            tier=tier,
            customer_id=customer_id
        )

        # Verify the package
        verification_result = evidence_packager.verify_evidence_pack(package_path)

        return render_template('evidence_pack_created.html',
                             package_path=package_path,
                             package_hash=package_hash,
                             verification=verification_result,
                             lc_number=session['last_lc_data'].get('lc_number', 'Unknown'))

    except Exception as e:
        app.logger.error(f"Evidence pack creation error: {str(e)}")
        flash(f'Evidence pack creation failed: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/pricing')
def pricing():
    """Pricing and tier comparison"""
    pricing_info = tier_manager.get_upsell_pricing()
    return render_template('pricing.html', pricing=pricing_info)

@app.route('/api/customer-summary')
def api_customer_summary():
    """API endpoint for customer usage summary"""
    customer_id = request.args.get('customer_id', 'demo-user')
    tier = request.args.get('tier', 'free')

    try:
        summary = tier_manager.get_customer_summary(customer_id, tier)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """API endpoint for LC validation (sync processing)"""
    try:
        data = request.get_json()

        if not data or 'lc_document' not in data:
            return jsonify({"error": "Missing lc_document in request"}), 400

        customer_id = data.get('customer_id', 'api-user')
        tier = data.get('tier', 'free')
        bank_mode = data.get('bank_mode', '')

        # Enhanced validation with bank profile support
        if bank_mode and bank_profile_engine:
            # Use new bank profile engine for enforcement
            if compliance_integration:
                result = compliance_integration.validate_lc_compliance(
                    lc_document=data['lc_document'],
                    customer_id=customer_id,
                    tier=tier
                )
            else:
                result = mock_compliance_validation(data['lc_document'], customer_id, tier)

            # Apply bank-specific enforcement profile
            result = bank_profile_engine.apply_bank_profile(result, bank_mode)

            # Add bank profile information to response
            bank_profile = bank_profile_engine.get_profile(bank_mode)
            if bank_profile:
                result['bank_profile'] = {
                    'bank_name': bank_profile.get('bank_name'),
                    'bank_code': bank_mode,
                    'enforcement_level': bank_profile.get('enforcement_config', {}).get('level'),
                    'category': bank_profile.get('category'),
                    'market_share': bank_profile.get('market_share'),
                    'description': bank_profile.get('enforcement_config', {}).get('description')
                }

                result['bank_recommendations'] = bank_profile.get('processing_expectations', {}).get('recommendations', [])
                result['processing_expectations'] = bank_profile.get('processing_expectations', {})

        elif bank_mode and bank_simulator:
            # Fallback to legacy bank simulator
            result = bank_simulator.validate_with_bank(data['lc_document'], bank_mode)
            result = convert_bank_result_to_standard(result, tier)
        elif compliance_integration:
            result = compliance_integration.validate_lc_compliance(
                lc_document=data['lc_document'],
                customer_id=customer_id,
                tier=tier
            )
        else:
            result = mock_compliance_validation(data['lc_document'], customer_id, tier)

        # Add plain English summary if requested
        if data.get('include_plain_english', False):
            result['plain_english_summary'] = output_layer.to_plain_english(result)

        # Add processing metadata
        result['processing_metadata'] = {
            'processing_mode': 'synchronous',
            'api_version': '2.4.0',
            'processed_at': datetime.now().isoformat(),
            'tier_used': tier
        }

        return jsonify(result)

    except Exception as e:
        app.logger.error(f"API validation error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/evidence-pack', methods=['POST'])
def api_evidence_pack():
    """API endpoint for evidence pack creation"""
    try:
        data = request.get_json()

        required_fields = ['lc_document', 'validation_result']
        if not all(field in data for field in required_fields):
            return jsonify({"error": f"Missing required fields: {required_fields}"}), 400

        customer_id = data.get('customer_id', 'api-user')
        tier = data.get('tier', 'free')

        # Check tier permissions
        tier_info = tier_manager.get_tier_info(tier)
        if not tier_info.evidence_packs:
            return jsonify({
                "error": "Evidence packs not available in current tier",
                "tier": tier,
                "upgrade_required": "pro"
            }), 403

        # Create evidence package
        package_path, package_hash = evidence_packager.create_evidence_pack(
            compliance_result=data['validation_result'],
            lc_document=data['lc_document'],
            tier=tier,
            customer_id=customer_id
        )

        return jsonify({
            "success": True,
            "package_path": package_path,
            "package_hash": package_hash,
            "lc_number": data['lc_document'].get('lc_number', 'Unknown')
        })

    except Exception as e:
        app.logger.error(f"API evidence pack error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    services = {
        "compliance_engine": "operational" if compliance_integration else "mock",
        "tier_manager": "operational",
        "evidence_packager": "operational",
        "bank_profile_engine": "operational" if bank_profile_engine else "unavailable"
    }

    # Check async processing health
    try:
        from async.api_integration import async_bp
        services["async_processing"] = "operational"
    except ImportError:
        services["async_processing"] = "unavailable"

    return jsonify({
        "status": "healthy",
        "version": "2.4.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "sync_validation": True,
            "async_processing": services["async_processing"] == "operational",
            "bank_profiles": services["bank_profile_engine"] == "operational",
            "white_labeling": True,
            "textract_fallback": True
        },
        "services": services,
        "branding": {
            "company_name": branding_config.get('company_name'),
            "environment": os.environ.get('ENVIRONMENT', 'development')
        }
    })

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html',
                         error_code=404,
                         error_message="Page not found"), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size exceeded errors"""
    flash('File too large. Maximum upload size is 10MB', 'error')
    return redirect(url_for('validate_lc'))

@app.errorhandler(500)
def server_error(error):
    app.logger.error(f"Server error: {str(error)}")
    return render_template('error.html',
                         error_code=500,
                         error_message="Internal server error"), 500

# Initialize session for demo users
@app.before_request
def init_session():
    if 'customer_id' not in session:
        # Create demo customer ID
        session['customer_id'] = f"demo-{secrets.token_hex(4)}"

    # Add user tier context for rate limiting
    if 'user_tier' not in session:
        session['user_tier'] = 'pro'  # Default to pro for demo

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path(__file__).parent / 'templates'
    templates_dir.mkdir(exist_ok=True)

    # Development server
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') == 'development'

    print(f"🚀 Starting LCopilot SME Portal on port {port}")
    print(f"📊 Dashboard: http://localhost:{port}/")
    print(f"🔍 Validation: http://localhost:{port}/validate")
    print(f"💰 Pricing: http://localhost:{port}/pricing")
    print(f"❤️  Health: http://localhost:{port}/health")

    app.run(host='0.0.0.0', port=port, debug=debug)