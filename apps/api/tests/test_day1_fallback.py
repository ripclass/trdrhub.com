from app.services.validation.day1_fallback import resolve_fallback_chain


def test_native_selected_when_threshold_met():
    native = {
        "issuer": {"normalized": "A"},
        "bin": {"normalized": "1"},
        "tin": {"normalized": "1"},
        "voyage": {"normalized": "V1"},
        "gross_weight": {"normalized_kg": 1000},
    }
    out = resolve_fallback_chain(native_fields=native, ocr_fields={}, llm_fields={})
    assert out.selected_stage == "native"
    assert out.llm_assist_required is False


def test_ocr_selected_when_native_low_coverage():
    native = {"issuer": {"normalized": "A"}}
    ocr = {
        "issuer": {"normalized": "A"},
        "bin": {"normalized": "1"},
        "tin": {"normalized": "1"},
        "voyage": {"normalized": "V1"},
        "gross_weight": {"normalized_kg": 1000},
    }
    out = resolve_fallback_chain(native_fields=native, ocr_fields=ocr, llm_fields={})
    assert out.selected_stage == "ocr"
    assert out.llm_assist_required is False


def test_llm_selected_when_native_and_ocr_low_coverage():
    native = {"issuer": {"normalized": "A"}}
    ocr = {"issuer": {"normalized": "A"}}
    llm = {
        "issuer": {"normalized": "A"},
        "bin": {"normalized": "1"},
        "tin": {"normalized": "1"},
        "voyage": {"normalized": "V1"},
        "gross_weight": {"normalized_kg": 1000},
    }
    out = resolve_fallback_chain(native_fields=native, ocr_fields=ocr, llm_fields=llm)
    assert out.selected_stage == "llm_assist"
    assert out.llm_assist_required is True
