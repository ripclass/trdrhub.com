from app.services.validation.day1_contract import enforce_day1_response_contract


def test_day1_contract_pass_when_no_violations():
    data = {
        "processing_summary_v2": {
            "documents": [
                {
                    "filename": "a.pdf",
                    "extraction_status": "success",
                    "day1_runtime": {"coverage": 6, "threshold": 5, "schema_ok": True, "errors": []},
                }
            ]
        }
    }
    out = enforce_day1_response_contract(data)
    assert out["_day1_contract"]["status"] == "pass"
    assert out["_day1_contract"]["documents_checked"] == 1
    assert out["_day1_contract"]["violations"] == []


def test_day1_contract_downgrades_success_on_low_coverage():
    data = {
        "processing_summary_v2": {
            "documents": [
                {
                    "filename": "b.pdf",
                    "extraction_status": "success",
                    "day1_runtime": {"coverage": 3, "threshold": 5, "schema_ok": True, "errors": []},
                }
            ]
        }
    }
    out = enforce_day1_response_contract(data)
    doc = out["processing_summary_v2"]["documents"][0]
    assert doc["extraction_status"] == "partial"
    assert out["_day1_contract"]["status"] == "review"
    assert any(v["code"] == "QA_REQUIRED_FIELD_EMPTY" for v in out["_day1_contract"]["violations"])


def test_day1_contract_flags_schema_violation_and_unknown_codes():
    data = {
        "documents": [
            {
                "filename": "c.pdf",
                "extraction_status": "success",
                "day1_runtime": {
                    "coverage": 6,
                    "threshold": 5,
                    "schema_ok": False,
                    "errors": ["NOT_MAPPED", "RET_NO_HIT", "RET_LOW_RELEVANCE"],
                },
            }
        ]
    }
    out = enforce_day1_response_contract(data)
    codes = [v["code"] for v in out["_day1_contract"]["violations"]]
    assert "PRM_OUTPUT_SCHEMA_VIOLATION" in codes
    assert "SYS_UNKNOWN" in codes
    assert out["_day1_metrics"]["ret_no_hit"] == 1
    assert out["_day1_metrics"]["ret_low_relevance"] == 1
