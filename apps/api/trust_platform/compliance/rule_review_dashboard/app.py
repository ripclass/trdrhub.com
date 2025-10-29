#!/usr/bin/env python3
"""
Rule Review Dashboard
Flask web application for reviewing and approving AI-suggested compliance rules.

Features:
- Upload ICC PDF documents
- View AI-generated rule suggestions
- Side-by-side comparison with article references
- Approve/Edit/Reject workflow
- Export to YAML rule files
- Git integration for version control
"""

import os
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Import our compliance modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from icc_parser import ICCDocumentParser, DocumentType
from ai_rule_suggester import AIRuleSuggester, SuggestionSession
from rule_linter import RuleLinter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rule_review.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize components
icc_parser = ICCDocumentParser()
ai_suggester = AIRuleSuggester()
rule_linter = RuleLinter()


# Database Models
class ParsedDocumentModel(db.Model):
    """Database model for parsed ICC documents"""
    __tablename__ = 'parsed_documents'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    document_version = db.Column(db.String(50))
    total_articles = db.Column(db.Integer)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    parsing_status = db.Column(db.String(50), default='pending')
    file_path = db.Column(db.String(500))
    parsed_data_path = db.Column(db.String(500))

    # Relationships
    suggestions = db.relationship('RuleSuggestionModel', backref='document', lazy=True)


class RuleSuggestionModel(db.Model):
    """Database model for AI rule suggestions"""
    __tablename__ = 'rule_suggestions'

    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    reference = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    dsl_expression = db.Column(db.Text)
    handler_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    confidence = db.Column(db.String(20), nullable=False)
    reasoning = db.Column(db.Text)
    review_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, modified
    reviewer_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    # Foreign key
    document_id = db.Column(db.Integer, db.ForeignKey('parsed_documents.id'), nullable=False)


class ReviewSessionModel(db.Model):
    """Database model for review sessions"""
    __tablename__ = 'review_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    reviewer_name = db.Column(db.String(100))
    document_id = db.Column(db.Integer, db.ForeignKey('parsed_documents.id'))
    total_suggestions = db.Column(db.Integer)
    approved_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    modified_count = db.Column(db.Integer, default=0)
    session_status = db.Column(db.String(20), default='active')  # active, completed, exported
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)


# Routes
@app.route('/')
def index():
    """Dashboard home page"""
    recent_documents = ParsedDocumentModel.query.order_by(ParsedDocumentModel.upload_timestamp.desc()).limit(10).all()
    pending_reviews = RuleSuggestionModel.query.filter_by(review_status='pending').count()
    approved_rules = RuleSuggestionModel.query.filter_by(review_status='approved').count()

    stats = {
        'total_documents': ParsedDocumentModel.query.count(),
        'pending_reviews': pending_reviews,
        'approved_rules': approved_rules,
        'completion_rate': round(approved_rules / max(1, approved_rules + pending_reviews) * 100, 1)
    }

    return render_template('index.html', recent_documents=recent_documents, stats=stats)


@app.route('/upload', methods=['GET', 'POST'])
def upload_document():
    """Upload and parse ICC documents"""
    if request.method == 'GET':
        return render_template('upload.html')

    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(request.url)

    if not file.filename.lower().endswith('.pdf'):
        flash('Only PDF files are supported', 'error')
        return redirect(request.url)

    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{filename}"
        file_path = app.config['UPLOAD_FOLDER'] / safe_filename
        file.save(str(file_path))

        # Create database record
        doc_record = ParsedDocumentModel(
            filename=filename,
            document_type='unknown',
            file_path=str(file_path),
            parsing_status='parsing'
        )
        db.session.add(doc_record)
        db.session.commit()

        # Parse document in background (simplified - would use Celery in production)
        try:
            parsed_doc = icc_parser.parse_document(file_path)

            # Update database record
            doc_record.document_type = parsed_doc.document_type.value
            doc_record.document_version = parsed_doc.document_version
            doc_record.total_articles = len(parsed_doc.articles)
            doc_record.parsing_status = 'completed'

            # Generate AI suggestions
            if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
                suggestion_session = ai_suggester.suggest_rules_from_document(parsed_doc)

                # Save suggestions to database
                for suggestion in suggestion_session.suggestions:
                    suggestion_record = RuleSuggestionModel(
                        rule_id=suggestion.rule_id,
                        title=suggestion.title,
                        reference=suggestion.reference,
                        severity=suggestion.severity,
                        dsl_expression=suggestion.dsl_expression,
                        handler_name=suggestion.handler_name,
                        description=suggestion.suggested_description,
                        confidence=suggestion.confidence.value,
                        reasoning=suggestion.reasoning,
                        document_id=doc_record.id
                    )
                    db.session.add(suggestion_record)

            db.session.commit()

            flash(f'Successfully parsed {len(parsed_doc.articles)} articles from {filename}', 'success')
            return redirect(url_for('review_document', doc_id=doc_record.id))

        except Exception as parse_error:
            doc_record.parsing_status = 'failed'
            db.session.commit()
            logger.error(f"Parsing failed: {parse_error}")
            flash(f'Failed to parse document: {str(parse_error)}', 'error')

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        flash(f'Upload failed: {str(e)}', 'error')

    return redirect(url_for('upload_document'))


@app.route('/documents')
def list_documents():
    """List all parsed documents"""
    documents = ParsedDocumentModel.query.order_by(ParsedDocumentModel.upload_timestamp.desc()).all()
    return render_template('documents.html', documents=documents)


@app.route('/review/<int:doc_id>')
def review_document(doc_id: int):
    """Review AI suggestions for a specific document"""
    doc = ParsedDocumentModel.query.get_or_404(doc_id)
    suggestions = RuleSuggestionModel.query.filter_by(document_id=doc_id).all()

    # Group suggestions by confidence level
    suggestions_by_confidence = {
        'high': [s for s in suggestions if s.confidence == 'high'],
        'medium': [s for s in suggestions if s.confidence == 'medium'],
        'low': [s for s in suggestions if s.confidence == 'low'],
        'uncertain': [s for s in suggestions if s.confidence == 'uncertain']
    }

    return render_template('review.html',
                         document=doc,
                         suggestions=suggestions,
                         suggestions_by_confidence=suggestions_by_confidence)


@app.route('/api/suggestion/<int:suggestion_id>', methods=['GET', 'PUT'])
def handle_suggestion(suggestion_id: int):
    """API endpoint for getting/updating rule suggestions"""
    suggestion = RuleSuggestionModel.query.get_or_404(suggestion_id)

    if request.method == 'GET':
        return jsonify({
            'id': suggestion.id,
            'rule_id': suggestion.rule_id,
            'title': suggestion.title,
            'reference': suggestion.reference,
            'severity': suggestion.severity,
            'dsl_expression': suggestion.dsl_expression,
            'handler_name': suggestion.handler_name,
            'description': suggestion.description,
            'confidence': suggestion.confidence,
            'reasoning': suggestion.reasoning,
            'review_status': suggestion.review_status,
            'reviewer_notes': suggestion.reviewer_notes
        })

    elif request.method == 'PUT':
        data = request.get_json()
        action = data.get('action')  # approve, reject, modify

        if action == 'approve':
            suggestion.review_status = 'approved'
            suggestion.reviewed_at = datetime.utcnow()
        elif action == 'reject':
            suggestion.review_status = 'rejected'
            suggestion.reviewed_at = datetime.utcnow()
            suggestion.reviewer_notes = data.get('notes', '')
        elif action == 'modify':
            suggestion.review_status = 'modified'
            suggestion.reviewed_at = datetime.utcnow()
            # Update fields
            for field in ['title', 'severity', 'dsl_expression', 'handler_name', 'description']:
                if field in data:
                    setattr(suggestion, field, data[field])
            suggestion.reviewer_notes = data.get('notes', '')

        db.session.commit()
        return jsonify({'status': 'success', 'review_status': suggestion.review_status})


@app.route('/export/<int:doc_id>')
def export_rules(doc_id: int):
    """Export approved rules to YAML"""
    doc = ParsedDocumentModel.query.get_or_404(doc_id)
    approved_suggestions = RuleSuggestionModel.query.filter_by(
        document_id=doc_id,
        review_status='approved'
    ).all()

    modified_suggestions = RuleSuggestionModel.query.filter_by(
        document_id=doc_id,
        review_status='modified'
    ).all()

    all_approved = approved_suggestions + modified_suggestions

    if not all_approved:
        flash('No approved rules to export', 'warning')
        return redirect(url_for('review_document', doc_id=doc_id))

    # Create YAML content
    yaml_content = {
        'metadata': {
            'standard': doc.document_type.upper(),
            'version': f"{doc.document_version}-reviewed",
            'description': f'Human-reviewed {doc.document_type} compliance rules from AI suggestions',
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
            'review_info': {
                'source_document': doc.filename,
                'total_suggestions': len(doc.suggestions),
                'approved_rules': len(all_approved),
                'review_completion_rate': f"{len(all_approved)/len(doc.suggestions)*100:.1f}%"
            }
        },
        'rules': []
    }

    # Convert approved suggestions to YAML format
    for suggestion in all_approved:
        rule_data = {
            'id': suggestion.rule_id,
            'title': suggestion.title,
            'reference': suggestion.reference,
            'severity': suggestion.severity,
            'applies_to': ['credit'],  # Default, could be configurable
            'version': '1.0.0'
        }

        # Add DSL or handler
        if suggestion.dsl_expression:
            rule_data['dsl'] = suggestion.dsl_expression
        elif suggestion.handler_name:
            rule_data['check_handler'] = suggestion.handler_name

        # Add description
        if suggestion.description:
            rule_data['description'] = suggestion.description

        # Add reviewer notes as comments
        if suggestion.reviewer_notes:
            rule_data['reviewer_notes'] = suggestion.reviewer_notes

        # Add example placeholders
        rule_data['examples'] = {
            'pass': [f"fixtures/{suggestion.rule_id.lower().replace('-', '_')}_pass.json"],
            'fail': [f"fixtures/{suggestion.rule_id.lower().replace('-', '_')}_fail.json"]
        }

        yaml_content['rules'].append(rule_data)

    # Export to file
    import yaml
    export_dir = Path(__file__).parent / 'exports'
    export_dir.mkdir(exist_ok=True)

    filename = f"{doc.document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    export_path = export_dir / filename

    with open(export_path, 'w') as f:
        yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

    # Lint exported rules
    try:
        errors, warnings = rule_linter.lint_file(export_path)
        if errors:
            flash(f'Exported rules have {len(errors)} errors that need fixing', 'warning')
        elif warnings:
            flash(f'Exported rules have {len(warnings)} warnings to review', 'info')
        else:
            flash('Rules exported successfully with no linting issues', 'success')
    except Exception as lint_error:
        flash(f'Rules exported but linting failed: {lint_error}', 'warning')

    return send_file(export_path, as_attachment=True, download_name=filename)


@app.route('/lint-check', methods=['POST'])
def lint_check():
    """API endpoint for real-time rule linting"""
    data = request.get_json()
    rule_text = data.get('rule_text', '')

    if not rule_text:
        return jsonify({'errors': ['No rule text provided'], 'warnings': []})

    try:
        # Create temporary YAML file for linting
        import tempfile
        import yaml

        temp_rule = {
            'metadata': {'standard': 'TEST', 'version': '1.0.0', 'description': 'Test rule'},
            'rules': [yaml.safe_load(rule_text)]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(temp_rule, f)
            temp_path = Path(f.name)

        errors, warnings = rule_linter.lint_file(temp_path)

        # Clean up
        temp_path.unlink()

        return jsonify({
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0
        })

    except Exception as e:
        return jsonify({
            'errors': [f'Linting error: {str(e)}'],
            'warnings': [],
            'valid': False
        })


# Template context processors
@app.context_processor
def inject_helpers():
    """Inject helper functions into templates"""
    return {
        'enumerate': enumerate,
        'len': len,
        'datetime': datetime
    }


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error="Internal server error"), 500


# CLI commands
@app.cli.command()
def init_db():
    """Initialize database tables"""
    db.create_all()
    print("Database initialized successfully")


@app.cli.command()
def reset_db():
    """Reset database (WARNING: deletes all data)"""
    db.drop_all()
    db.create_all()
    print("Database reset successfully")


if __name__ == '__main__':
    # Create tables
    with app.app_context():
        db.create_all()

    # Run development server
    app.run(debug=True, host='0.0.0.0', port=5001)