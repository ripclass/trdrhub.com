from app.services.validation.amendment_generator import generate_amendment_for_discrepancy


def test_does_not_generate_port_amendment_for_bin_missing_issue():
    discrepancy = {
        "rule": "crossdoc-bin-001",
        "title": "Exporter BIN Missing from Documents",
        "message": "BIN '000334455-0103' ON ALL DOCUMENTS → COMMERCIAL INVOICE=MISSING; BILL OF LADING=MISSING; PACKING LIST=MISSING; CERTIFICATE OF ORIGIN=MISSING",
        "expected": "EXPORTER BIN: 000334455-0103 MUST APPEAR ON ALL DOCUMENTS",
        "found": "Commercial Invoice=missing; Bill of Lading=missing; Packing List=missing; Certificate of Origin=missing",
    }
    lc_data = {"lc_number": "EXP2026BD001", "port_of_loading": "Chattogram"}

    amendment = generate_amendment_for_discrepancy(discrepancy, lc_data)

    assert amendment is None


def test_generates_real_port_amendment_for_actual_port_mismatch():
    discrepancy = {
        "rule": "crossdoc-bl-001",
        "title": "Port of Loading Mismatch",
        "message": "Bill of Lading port of loading does not match LC requirements.",
        "expected": "Port of Loading: CHITTAGONG",
        "found": "Port of Loading: MONGLA",
    }
    lc_data = {"lc_number": "EXP2026BD001"}

    amendment = generate_amendment_for_discrepancy(discrepancy, lc_data)

    assert amendment is not None
    assert amendment.field_tag == "44E"
    assert amendment.field_name == "Port of Loading"
    assert amendment.current_value == "CHITTAGONG"
    assert amendment.proposed_value == "MONGLA"
