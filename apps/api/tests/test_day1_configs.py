from app.services.validation.day1_configs import (
    load_day1_schema,
    load_day1_anchors,
    load_day1_reason_codes,
    load_day1_telemetry_events,
)


def test_day1_schema_loads_and_version_matches():
    schema = load_day1_schema()
    assert schema["properties"]["meta"]["properties"]["schema_version"]["const"] == "v1.0.0-day1"


def test_day1_anchors_has_required_keys():
    data = load_day1_anchors()
    keys = {e["key"] for e in data["anchor_dictionary_v1"]["entities"]}
    assert {"bin_tin", "bl_voyage", "gross_weight", "net_weight", "issuer"}.issubset(keys)


def test_day1_reason_codes_has_hallucination_code():
    data = load_day1_reason_codes()
    assert "PRM_HALLUCINATED_VALUE" in data["reason_code_enum_v1"]["values"]


def test_day1_telemetry_has_pipeline_completed():
    data = load_day1_telemetry_events()
    names = {e["name"] for e in data["telemetry_events_v1"]["events"]}
    assert "pipeline_completed" in names
