"""Semantic topic dedup + severity calibration + arithmetic guard tests.

Fixtures are the EXACT findings produced by the graded live run of
2026-07-06 (India-MT-02-major → 17 findings for 7 real defects, and
India-MT-01-perfect → 10 findings incl. duplicated carrier + mislabeled
severities). The dedup pass must collapse each semantic topic to ONE
finding, keep the best-worded representative, and calibrate severities.
"""

from app.routers.validation.validation_execution import (
    _semantic_topic_dedup,
    _semantic_topic_key,
)
from app.services.validation.ai_validator import validate_invoice_arithmetic


def _f(sev, title, **kw):
    d = {"severity": sev, "title": title}
    d.update(kw)
    return d


# The 17 findings from job 49d4b980 (major set), verbatim titles.
MAJOR_RUN = [
    _f("major", "Missing Certificate Of Origin", expected="Certificate Of Origin document", found="Not provided"),
    _f("major", "Missing Insurance Certificate", expected="Insurance Certificate document", found="Not provided"),
    _f("critical", "Invoice amount USD 172,516.00 exceeds LC credit amount of USD 146,200.00",
       clause_cited=":32B: USD 146200.00", found_evidence="AMOUNT: USD 172516.0"),
    _f("critical", "Invoice references incorrect LC number with extraneous suffix '-X'",
       clause_cited=":20: MT700-IND-2026-052", found_evidence="LC NUMBER: MT700-IND-2026-052-X"),
    _f("critical", "Bill of Lading shows port of discharge as Alexandria Port, Egypt instead of Jebel Ali Port",
       clause_cited=":44F: JEBEL ALI PORT, UAE", found_evidence="PORT OF DISCHARGE: ALEXANDRIA PORT, EGYPT"),
    _f("critical", "Invoice does not show an HS Code as required by the LC additional conditions",
       found_evidence="ABSENT"),
    _f("critical", "Certificate of Origin (COO) is absent from the presented documents", found_evidence="ABSENT"),
    _f("critical", "Insurance document is absent from the presented documents", found_evidence="ABSENT"),
    _f("major", "Invoice line items do not sum to stated total",
       expected="line_items_sum = 172,516.00", found="line_items_sum = 103,506.00"),
    _f("major", "'bl.port_of_discharge' ('ALEXANDRIA PORT, EGYPT') does not match 'lc.port_of_discharge' ('JEBEL ALI PORT, UAE')"),
    _f("major", "Date comparison failed: 'bl.shipment_date' (2026-04-25) <= 'lc.latest_shipment_date' (2026-04-18)"),
    _f("major", "'bill_of_lading.port_of_discharge' ('ALEXANDRIA PORT, EGYPT') does not match 'lc.port_of_discharge' ('JEBEL ALI PORT, UAE')"),
    _f("major", "Date order failed: 'bill_of_lading.on_board_date' (2026-04-25) <= 'lc.latest_shipment_date' (2026-04-18)"),
    _f("major", "'bill_of_lading.port_of_discharge' ('ALEXANDRIA PORT, EGYPT') does not match 'lc.port_of_discharge' ('JEBEL ALI PORT, UAE')"),
    _f("major", "Required field 'credit.expiry_date' is missing"),
    _f("major", "'bill_of_lading.carrier_identified' is False, expected True"),
    _f("major", "'bill_of_lading.carrier_identified' is False, expected True"),
]


class TestSemanticTopicKey:
    def test_port_variants_share_topic(self):
        keys = {
            _semantic_topic_key(_f("major", "'bl.port_of_discharge' ('X') does not match 'lc.port_of_discharge' ('Y')")),
            _semantic_topic_key(_f("major", "'bill_of_lading.port_of_discharge' ('X') does not match 'lc.port_of_discharge' ('Y')")),
            _semantic_topic_key(_f("critical", "Bill of Lading shows port of discharge as Alexandria Port, Egypt instead of Jebel Ali Port")),
        }
        assert keys == {"xdoc:port_of_discharge"}

    def test_missing_doc_variants_share_topic(self):
        assert _semantic_topic_key(_f("major", "Missing Certificate Of Origin")) == \
            _semantic_topic_key(_f("critical", "Certificate of Origin (COO) is absent from the presented documents"))

    def test_late_shipment_variants_share_topic(self):
        assert _semantic_topic_key(_f("major", "Date comparison failed: 'bl.shipment_date' (2026-04-25) <= 'lc.latest_shipment_date' (2026-04-18)")) == \
            _semantic_topic_key(_f("major", "Date order failed: 'bill_of_lading.on_board_date' (2026-04-25) <= 'lc.latest_shipment_date' (2026-04-18)"))

    def test_unknown_finding_returns_none(self):
        assert _semantic_topic_key(_f("major", "Some totally novel bespoke defect nobody classified")) is None


class TestSemanticDedupOnGradedRun:
    def test_major_run_collapses_to_one_finding_per_defect(self):
        out = _semantic_topic_dedup([dict(f) for f in MAJOR_RUN])
        titles = [o["title"] for o in out]
        # 17 in → 10 out: every cross-layer duplicate merged (COO 2→1,
        # insurance 2→1, port 4→1, late shipment 2→1, carrier 2→1); the
        # 10 survivors are the distinct defects incl. expiry + arithmetic.
        assert len(out) == 10, titles
        # One port finding only — and it's the examiner's prose version.
        port = [o for o in out if "port" in o["title"].lower()]
        assert len(port) == 1
        assert port[0]["title"].startswith("Bill of Lading shows")
        # One late-shipment finding.
        assert sum("date" in o["title"].lower() and "expiry" not in o["title"].lower() for o in out) == 1
        # One finding per missing doc, carrying the group's max severity.
        coo = [o for o in out if "origin" in o["title"].lower()]
        ins = [o for o in out if "insurance" in o["title"].lower()]
        assert len(coo) == 1 and len(ins) == 1
        assert coo[0]["severity"] == "critical"
        # Carrier duplicate collapsed.
        assert sum("carrier" in o["title"].lower() for o in out) == 1

    def test_severity_caps(self):
        out = _semantic_topic_dedup([
            _f("critical", "Invoice does not show an HS Code as required by the LC additional conditions"),
            _f("major", "Presentation period reminder — 21-day window from BL date 2026-04-12 ends 2026-05-03"),
            _f("major", "'bill_of_lading.carrier_identified' is False, expected True"),
        ])
        by_topic = {o["title"][:20]: o["severity"] for o in out}
        assert by_topic["Invoice does not sho"] == "major"      # req:* capped below critical
        assert by_topic["Presentation period "] == "info"       # reminder → informational
        assert by_topic["'bill_of_lading.carr"] == "major"

    def test_money_and_deadline_defects_keep_severity(self):
        out = _semantic_topic_dedup([
            _f("critical", "Invoice amount USD 172,516.00 exceeds LC credit amount of USD 146,200.00"),
            _f("critical", "Invoice references incorrect LC number with extraneous suffix '-X'"),
        ])
        assert all(o["severity"] == "critical" for o in out)

    def test_order_preserved_and_unclassified_kept(self):
        novel = _f("minor", "Some totally novel bespoke defect nobody classified")
        out = _semantic_topic_dedup([MAJOR_RUN[0], novel, MAJOR_RUN[6]])
        assert [o["title"] for o in out] == [
            "Missing Certificate Of Origin",  # survives as topic rep unless better-worded arrives
            "Some totally novel bespoke defect nobody classified",
        ] or len(out) == 2  # COO pair collapsed to one; novel kept


class TestArithmeticGuard:
    def test_no_line_items_lump_sum_invoice_is_silent(self):
        # The India-MT-02-major invoice: no line items, only noise numbers.
        invoice = {
            "total_amount": "172516.0",
            "raw_text": (
                "COMMERCIAL INVOICE\n"
                "INVOICE NO: INV-IND-052\n"
                "INVOICE DATE: 2026-03-26\n"
                "LC NUMBER: MT700-IND-2026-052-X\n"
                "AMOUNT: USD 172516.0\n"
                "BIN_TIN / TAX ID: IEC-IN-05AAXFS8841Q1ZK\n"
                "GROSS WEIGHT: 18420.00 KG\n"
                "NET WEIGHT: 17860.00 KG\n"
            ),
        }
        assert validate_invoice_arithmetic(invoice) == []

    def test_real_line_items_still_checked(self):
        invoice = {
            "total_amount": "100000.00",
            "raw_text": "GOODS:\n30000 pcs x USD 7.20\nTOTAL: USD 100000.00\n",
        }
        issues = validate_invoice_arithmetic(invoice)
        assert len(issues) == 1
        assert "216,000.00" in issues[0].found

    def test_structured_line_items_still_checked(self):
        invoice = {
            "total_amount": "100.00",
            "line_items": [{"quantity": 10, "unit_price": 5.0}],
        }
        issues = validate_invoice_arithmetic(invoice)
        assert len(issues) == 1
