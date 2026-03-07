from app.services.validation.day1_telemetry import build_day1_metrics


def test_day1_telemetry_counts_ret_codes():
    structured = {
        "documents": [
            {"extraction_status": "success", "day1_runtime": {"errors": ["RET_NO_HIT", "RET_LOW_RELEVANCE"]}},
            {"extraction_status": "partial", "day1_runtime": {"errors": ["RET_NO_HIT"]}},
        ]
    }
    out = build_day1_metrics(structured)
    assert out["documents_total"] == 2
    assert out["status_counts"]["success"] == 1
    assert out["status_counts"]["partial"] == 1
    assert out["ret_no_hit"] == 2
    assert out["ret_low_relevance"] == 1
