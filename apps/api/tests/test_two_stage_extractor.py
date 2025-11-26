"""
Tests for two-stage extraction pipeline.
"""

import pytest
from app.services.extraction.two_stage_extractor import (
    TwoStageExtractor,
    ExtractedField,
    ExtractionStatus,
    FieldType,
    FieldValidator,
    two_stage_extract,
)


class TestFieldValidator:
    """Tests for field validation."""
    
    def setup_method(self):
        self.validator = FieldValidator()
    
    def test_validate_lc_number_valid(self):
        field = ExtractedField(
            name="lc_number",
            field_type=FieldType.LC_NUMBER,
            raw_value="EXP2026BD001",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert not issues
        assert field.normalized_value == "EXP2026BD001"
    
    def test_validate_lc_number_too_short(self):
        field = ExtractedField(
            name="lc_number",
            field_type=FieldType.LC_NUMBER,
            raw_value="ABC",
        )
        score, issues = self.validator.validate(field)
        assert score < 1.0
        assert "too short" in issues[0].lower()
    
    def test_validate_amount_valid(self):
        field = ExtractedField(
            name="amount",
            field_type=FieldType.AMOUNT,
            raw_value="125,000.00",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert not issues
        assert field.normalized_value == 125000.0
    
    def test_validate_amount_numeric(self):
        field = ExtractedField(
            name="amount",
            field_type=FieldType.AMOUNT,
            raw_value=50000.50,
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == 50000.50
    
    def test_validate_amount_invalid(self):
        field = ExtractedField(
            name="amount",
            field_type=FieldType.AMOUNT,
            raw_value="not a number",
        )
        score, issues = self.validator.validate(field)
        assert score == 0.0
        assert "parse" in issues[0].lower()
    
    def test_validate_currency_valid(self):
        field = ExtractedField(
            name="currency",
            field_type=FieldType.CURRENCY,
            raw_value="USD",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == "USD"
    
    def test_validate_currency_alias(self):
        field = ExtractedField(
            name="currency",
            field_type=FieldType.CURRENCY,
            raw_value="DOLLAR",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == "USD"
    
    def test_validate_currency_invalid(self):
        field = ExtractedField(
            name="currency",
            field_type=FieldType.CURRENCY,
            raw_value="XYZ",
        )
        score, issues = self.validator.validate(field)
        assert score < 1.0
        assert "unknown" in issues[0].lower()
    
    def test_validate_port_known(self):
        field = ExtractedField(
            name="port",
            field_type=FieldType.PORT,
            raw_value="Chittagong",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert "Chittagong" in field.normalized_value
    
    def test_validate_port_alias(self):
        field = ExtractedField(
            name="port",
            field_type=FieldType.PORT,
            raw_value="Chattogram",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert "Chittagong" in field.normalized_value
    
    def test_validate_date_iso(self):
        field = ExtractedField(
            name="date",
            field_type=FieldType.DATE,
            raw_value="2026-03-15",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == "2026-03-15"
    
    def test_validate_date_dmy(self):
        field = ExtractedField(
            name="date",
            field_type=FieldType.DATE,
            raw_value="15/03/2026",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == "2026-03-15"
    
    def test_validate_swift_valid(self):
        field = ExtractedField(
            name="swift",
            field_type=FieldType.SWIFT_CODE,
            raw_value="SCBLBDDX",
        )
        score, issues = self.validator.validate(field)
        assert score == 1.0
        assert field.normalized_value == "SCBLBDDX"
    
    def test_validate_swift_invalid(self):
        field = ExtractedField(
            name="swift",
            field_type=FieldType.SWIFT_CODE,
            raw_value="ABC",
        )
        score, issues = self.validator.validate(field)
        assert score < 1.0
        assert "8 or 11" in issues[0]


class TestTwoStageExtractor:
    """Tests for the full two-stage pipeline."""
    
    def setup_method(self):
        self.extractor = TwoStageExtractor()
    
    def test_process_lc_fields(self):
        ai_extraction = {
            "lc_number": {"value": "EXP2026BD001", "confidence": 0.95},
            "amount": {"value": "125000.00", "confidence": 0.90},
            "currency": {"value": "USD", "confidence": 0.99},
            "port_of_loading": {"value": "Chittagong", "confidence": 0.85},
        }
        
        results = self.extractor.process(ai_extraction, "lc")
        
        # All fields should be extracted
        assert len(results) == 4
        
        # High confidence + good validation = trusted
        assert results["lc_number"].status == ExtractionStatus.TRUSTED
        assert results["currency"].status == ExtractionStatus.TRUSTED
        
        # Check normalization happened
        assert results["lc_number"].normalized_value == "EXP2026BD001"
        assert results["currency"].normalized_value == "USD"
    
    def test_process_low_confidence(self):
        ai_extraction = {
            "lc_number": {"value": "MAYBE123", "confidence": 0.3},
        }
        
        results = self.extractor.process(ai_extraction, "lc")
        
        # Low AI confidence = not trusted
        assert results["lc_number"].status in [
            ExtractionStatus.REVIEW,
            ExtractionStatus.UNTRUSTED,
        ]
    
    def test_process_invalid_value(self):
        ai_extraction = {
            "currency": {"value": "INVALID", "confidence": 0.9},
        }
        
        results = self.extractor.process(ai_extraction, "lc")
        
        # High AI confidence but validation failed
        assert results["currency"].status != ExtractionStatus.TRUSTED
        assert results["currency"].issues
    
    def test_extraction_summary(self):
        ai_extraction = {
            "lc_number": {"value": "EXP2026BD001", "confidence": 0.95},
            "amount": {"value": "125000", "confidence": 0.90},
            "currency": {"value": "INVALID", "confidence": 0.80},
        }
        
        results = self.extractor.process(ai_extraction, "lc")
        summary = self.extractor.get_extraction_summary(results)
        
        assert summary["total"] == 3
        assert summary["trusted"] >= 1
        assert "avg_confidence" in summary


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_two_stage_extract(self):
        ai_results = {
            "lc_number": {"value": "TEST123", "confidence": 0.8},
            "amount": 50000.0,  # Raw value without dict
        }
        
        fields, summary = two_stage_extract(ai_results, "lc")
        
        assert len(fields) == 2
        assert "total" in summary
        assert summary["total"] == 2

