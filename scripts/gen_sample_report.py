"""Generate the sample redacted LCopilot report for the /lcopilot landing.

Renders the REAL report template (apps/api/app/services/lc_report.py) with
redacted, realistic findings modeled on the IDEAL SAMPLE pilot pack, writing
apps/web/public/samples/lcopilot-sample-report.html. Re-run whenever the
template changes so the downloadable sample never drifts from the deliverable.

The module is loaded standalone by path — no `app` package init needed, so
this runs on a bare venv. PDF: WeasyPrint if available; otherwise print the
HTML to PDF with headless Edge/Chrome:

  msedge --headless --disable-gpu --no-pdf-header-footer \
    --print-to-pdf=apps/web/public/samples/lcopilot-sample-report.pdf \
    file:///.../apps/web/public/samples/lcopilot-sample-report.html
"""
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
MOD_PATH = REPO / "apps" / "api" / "app" / "services" / "lc_report.py"
OUT_DIR = REPO / "apps" / "web" / "public" / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("lc_report_standalone", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

structured_result = {
    "lc_number": "ILC/XXXX/2026/REDACTED",
    "bank_verdict": {"status": "discrepancies found"},
    "issues": [
        {
            "severity": "critical",
            "title": "Invoice total does not equal the sum of line items",
            "rule": "ARITHMETIC-1",
            "document_type": "commercial_invoice",
            "clause_cited": "45A: TOTAL VALUE USD 61,700.00 CFR REDACTED PORT",
            "expected": "Sum of quantity x unit price across all line items = stated invoice total",
            "found_evidence": "Line items total USD 60,950.00; invoice states USD 61,700.00 (difference USD 750.00)",
            "suggested_fix": "Reissue the commercial invoice with the total corrected to the line-item sum, or correct the unit price on item 3 if the stated total is the intended contract value.",
        },
        {
            "severity": "critical",
            "title": "Bill of lading not marked CLEAN ON BOARD",
            "rule": "UCP600-27",
            "document_type": "bill_of_lading",
            "clause_cited": "46A: FULL SET OF CLEAN ON BOARD OCEAN BILLS OF LADING",
            "expected": "An on-board notation with no clause declaring a defective condition of goods or packaging",
            "found_evidence": "B/L carries 'SHIPPED ON BOARD 12 JUN 2026' but no CLEAN notation; margin remark 'two cartons re-taped' present",
            "suggested_fix": "Request the carrier reissue the B/L without the defective-condition remark, or obtain the applicant's written waiver before presentation.",
        },
        {
            "severity": "major",
            "title": "Commercial invoice is unsigned",
            "rule": "ISBP821-A35",
            "document_type": "commercial_invoice",
            "clause_cited": "46A: SIGNED COMMERCIAL INVOICE IN 3 ORIGINALS",
            "expected": "Manually signed invoice, as the credit expressly requires a signed invoice",
            "found_evidence": "Presented invoice bears a printed name block but no signature",
            "suggested_fix": "Have the authorised signatory sign all three originals before presentation.",
        },
        {
            "severity": "major",
            "title": "Inspection certificate dated after shipment date",
            "rule": "UCP600-14",
            "document_type": "inspection_certificate",
            "clause_cited": "47A: PRE-SHIPMENT INSPECTION CERTIFICATE ISSUED BY [REDACTED]",
            "expected": "Inspection performed and certificate issued on or before the B/L on-board date (12 Jun 2026)",
            "found_evidence": "Certificate states inspection date 14 Jun 2026 — two days after shipment",
            "suggested_fix": "Obtain a corrected certificate showing the actual pre-shipment inspection date, or a replacement inspection consistent with the credit terms.",
        },
        {
            "severity": "minor",
            "title": "Packing list lacks carton-wise breakdown",
            "rule": "ISBP821-M2",
            "document_type": "packing_list",
            "clause_cited": "46A: DETAILED PACKING LIST IN 2 ORIGINALS SHOWING CARTON-WISE PACKING",
            "expected": "Per-carton contents, net weight and gross weight as the credit requires",
            "found_evidence": "Packing list shows totals per style only; no carton-level detail",
            "suggested_fix": "Reissue the packing list with the carton-wise breakdown the credit asks for.",
        },
        {
            "severity": "advisory",
            "title": "Insurance certificate presented under CFR terms",
            "rule": "CROSSDOC-INS-1",
            "document_type": "insurance_certificate",
            "clause_cited": "45A: ... CFR REDACTED PORT (Incoterms 2020)",
            "expected": "Under CFR the buyer arranges insurance; the credit does not call for an insurance document",
            "found_evidence": "An insurance certificate was included in the presentation set",
            "suggested_fix": "No action required by the bank, but presenting uncalled-for documents can invite scrutiny — consider omitting it.",
        },
    ],
}

review_note = (
    "Two critical discrepancies (findings 1 and 2) would very likely cause refusal "
    "under UCP 600 Art. 16 — fix these before presenting. The unsigned invoice and "
    "the inspection date are also refusal-grade but quick to cure. Names, ports and "
    "references in this sample are redacted from a real review."
)

html_content = mod.build_report_html(None, structured_result, review_note)

# Watermark it as a sample right in the header sub-line.
html_content = html_content.replace(
    "TRDR Hub · LCopilot — pre-presentation examination",
    "TRDR Hub · LCopilot — pre-presentation examination · SAMPLE (REDACTED)",
)

html_path = OUT_DIR / "lcopilot-sample-report.html"
html_path.write_text(html_content, encoding="utf-8")
print(f"HTML written: {html_path}")

pdf_bytes = mod._html_to_pdf(html_content)
if pdf_bytes:
    pdf_path = OUT_DIR / "lcopilot-sample-report.pdf"
    pdf_path.write_bytes(pdf_bytes)
    print(f"PDF written: {pdf_path} ({len(pdf_bytes)} bytes)")
else:
    print("WeasyPrint unavailable — HTML only")
