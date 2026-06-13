"""
PDF renderers for importer corpus.

Uses ReportLab (pure Python, no GTK/cairo) so the generator works on
Windows without system-lib gymnastics. Output format mirrors the shape
of real SWIFT MT700 messages captured from production corridors.

Three modes per LC:
  DRAFT_CLEAN   — draft LC, pre-issuance, no intentional issues
  DRAFT_RISKY   — draft LC with red-flag clauses the examiner should flag
  SHIPMENT_CLEAN — full presentation bundle (LC + invoice + BL + PL +
                   CoO + insurance + inspection), consistent end-to-end
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------
# Shared styles
# --------------------------------------------------------------------------

_BASE_STYLES = getSampleStyleSheet()

_STYLE_TITLE = ParagraphStyle(
    "DocTitle",
    parent=_BASE_STYLES["Heading1"],
    fontSize=14,
    spaceAfter=6,
    textColor=colors.HexColor("#111827"),
)
_STYLE_SECTION = ParagraphStyle(
    "DocSection",
    parent=_BASE_STYLES["Heading3"],
    fontSize=10,
    spaceBefore=8,
    spaceAfter=4,
    textColor=colors.HexColor("#374151"),
)
_STYLE_BODY = ParagraphStyle(
    "DocBody",
    parent=_BASE_STYLES["BodyText"],
    fontSize=9,
    leading=12,
    spaceAfter=2,
)
_STYLE_TAG = ParagraphStyle(
    "MT700Tag",
    parent=_BASE_STYLES["BodyText"],
    fontName="Courier-Bold",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#1f2937"),
)
_STYLE_TAG_VAL = ParagraphStyle(
    "MT700TagVal",
    parent=_BASE_STYLES["BodyText"],
    fontName="Courier",
    fontSize=8,
    leading=10,
    spaceAfter=3,
    textColor=colors.HexColor("#111827"),
)
_STYLE_DRAFT_WARN = ParagraphStyle(
    "DraftWarn",
    parent=_BASE_STYLES["Heading2"],
    fontSize=13,
    textColor=colors.HexColor("#9a3412"),
    alignment=1,  # center
    spaceAfter=6,
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _mt700_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{y[2:]}{m}{d}"


def _fmt_amount(num: str | float) -> str:
    return f"{Decimal(str(num)):,.2f}"


def _line_amount(item: Dict[str, Any]) -> Decimal:
    return Decimal(str(item["qty"])) * Decimal(str(item["unit_price"]))


def _total_amount(items: List[Dict[str, Any]]) -> Decimal:
    return sum((_line_amount(i) for i in items), Decimal("0"))


def _cartons_for(qty: int) -> int:
    """Cartons for a line item — ~100 pcs per carton, minimum one.

    THE single source of the carton formula. The packing list's
    carton-wise breakdown and the bill of lading's package count must
    both derive from this, or the SHIPMENT_CLEAN sets fail the PL↔BL
    carton cross-check (live CROSSDOC-PKL-LC-4, 2026-06-12: BL said
    "4,500 packages" — the piece count — while the PL said 45 cartons).
    """
    return max(1, qty // 100)


def _total_cartons(items: List[Dict[str, Any]]) -> int:
    return sum(_cartons_for(i["qty"]) for i in items)


_STYLE_TAG_LINE = ParagraphStyle(
    "MT700TagLine",
    parent=_BASE_STYLES["BodyText"],
    fontName="Courier",
    fontSize=8,
    leading=11,
    spaceAfter=4,
    leftIndent=0,
    firstLineIndent=0,
    textColor=colors.HexColor("#111827"),
)


def _field_lines(pairs: List[tuple[str, str]]) -> List:
    """Render plain-document [label, value] pairs as single-line paragraphs.

    Same anti-table-column-confusion fix as `_tag_lines`, but for non-MT700
    documents (invoice, BL, packing list, etc.) that use English labels
    rather than SWIFT tag codes. Each pair becomes one Paragraph; long
    values wrap at whitespace within their own paragraph and never collide
    with the next field's label.
    """
    flow = []
    for label, val in pairs:
        formatted_val = val.replace("<br/>", "<br/>&nbsp;&nbsp;&nbsp;")
        line_html = (
            f"<font face='Helvetica-Bold'>{label}:</font> {formatted_val}"
        )
        flow.append(Paragraph(line_html, _STYLE_TAG_LINE))
    return flow


def _tag_lines(pairs: List[tuple[str, str]]) -> List:
    """Render [tag_code, value] pairs as canonical SWIFT MT700 lines.

    Replaces the older 2-column ReportLab Table layout. The Table
    rendered each field as label-cell-then-value-cell; long labels
    wrapped to multiple visual lines while values stayed in the
    adjacent cell, so pdftotext / vision-LLM linearization produced
    'label-fragment value label-fragment value' streams that the
    extractor mis-parsed (e.g. read SWIFT field code '41' from
    '41D Available With' as the LC amount value).

    The new layout is one Paragraph per field, label inline with
    value, label as bold Courier and value as regular Courier. When
    a value is long enough to wrap, the wrapped continuation never
    collides with the next field's label because each field is its
    own Paragraph block.

    `tag` here is just the SWIFT tag code (e.g. '32B'), matching real
    MT700 wire format where the descriptive English label is human
    annotation, not part of the message.
    """
    flow = []
    for tag, val in pairs:
        # ReportLab Paragraph treats <br/> as a line break; preserve
        # those for multi-line values like applicant addresses.
        # Indent continuation lines so they're visually under the value.
        formatted_val = val.replace("<br/>", "<br/>&nbsp;&nbsp;&nbsp;")
        line_html = (
            f"<font face='Courier-Bold'>:{tag}:</font> {formatted_val}"
        )
        flow.append(Paragraph(line_html, _STYLE_TAG_LINE))
    return flow


def _doc(path: Path, title: str) -> SimpleDocTemplate:
    path.parent.mkdir(parents=True, exist_ok=True)
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
    )


# --------------------------------------------------------------------------
# LC (MT700) renderer
# --------------------------------------------------------------------------

def _apply_risky_mods(c: Dict[str, Any]) -> Dict[str, Any]:
    """Clone a corridor config and inject red-flag clauses the examiner
    should catch — tight presentation window, partial-shipments/insurance
    conflict, a missing 47A sanctions block, an impossible Incoterm +
    freight-term combination.
    """
    risky = dict(c)
    risky["lc_number"] = c["lc_number"] + "-RISKY"
    risky["presentation_period_days"] = 5  # aggressive; UCP default 21
    risky["partial_shipments"] = "ALLOWED"
    # Broken Incoterm + freight combo (CFR says seller pays freight, but
    # BL will be instructed as FREIGHT COLLECT below).
    risky_docs = list(c["documents_required"])
    # Force a BL instruction that conflicts with the Incoterm.
    risky_docs = [
        (
            d.replace("FREIGHT PREPAID", "FREIGHT COLLECT")
             if "BILL OF LADING" in d else d
        )
        for d in risky_docs
    ]
    # Drop the country-of-origin labelling requirement (common omission).
    risky_docs = [d for d in risky_docs if "COUNTRY OF ORIGIN" not in d]
    risky["documents_required"] = risky_docs
    # Strip the sanctions clause from 47A (the examiner should flag the
    # missing compliance statement).
    risky["additional_conditions"] = [
        ac for ac in c["additional_conditions"] if "SANCTION" not in ac
    ]
    risky["additional_conditions"].append(
        f"({len(risky['additional_conditions']) + 1}) DOCUMENTS MUST BE "
        f"PRESENTED WITHIN 5 DAYS OF SHIPMENT DATE BUT WITHIN LC VALIDITY."
    )
    return risky


def _lc_flow(c: Dict[str, Any], mode: str) -> List:
    """Build the MT700 content as a list of Flowables."""
    flow: List = []

    if mode == "DRAFT_CLEAN":
        flow.append(Paragraph(
            "*** DRAFT — NOT YET ISSUED / SUBJECT TO APPLICANT APPROVAL ***",
            _STYLE_DRAFT_WARN,
        ))
    elif mode == "DRAFT_RISKY":
        flow.append(Paragraph(
            "*** DRAFT — NOT YET ISSUED / RISK REVIEW COPY ***",
            _STYLE_DRAFT_WARN,
        ))

    flow.append(Paragraph("SWIFT MT700 — Issue of a Documentary Credit", _STYLE_TITLE))
    flow.append(Paragraph(f"Sender: {c['sender_bic']} &nbsp;&nbsp;&nbsp; Receiver: {c['receiver_bic']}", _STYLE_BODY))
    flow.append(Spacer(1, 6))

    pairs: List[tuple[str, str]] = [
        ("27", "1/1"),
        ("40A", "IRREVOCABLE"),
        ("20", c["lc_number"]),
        ("31C", _mt700_date(c["issue_date"])),
        ("40E", c["applicable_rules"]),
        ("31D", f"{_mt700_date(c['expiry_date'])} {c['expiry_place']}"),
        ("50", f"{c['applicant_name']}<br/>{c['applicant_address']}"),
        ("59", f"{c['beneficiary_account_hint']}<br/>{c['beneficiary_name']}<br/>{c['beneficiary_address']}"),
        ("32B", f"{c['currency']} {c['amount']}"),
        ("41D", c["available_with"]),
        ("42C", "SIGHT"),
        ("42A", c["drawee_bic"]),
        ("43P", c["partial_shipments"]),
        ("43T", c["transhipment"]),
        ("44E", c["port_loading"]),
        ("44F", c["port_discharge"]),
        ("44B", c["final_destination"]),
        ("44C", _mt700_date(c["latest_shipment_date"])),
        ("45A", c["goods_description"]),
        ("46A", "<br/><br/>".join(c["documents_required"])),
        ("47A", "<br/><br/>".join(c["additional_conditions"])),
        ("71D", c["charges_clause"]),
        ("48", f"{c['presentation_period_days']}/FROM SHIPMENT BUT WITHIN LC EXPIRY"),
        ("49", c["confirmation"]),
        ("78", c["instructions_78"]),
        ("57A", c["advise_through_bic"]),
        ("72Z", "PLS ADVISE THE CREDIT TO THE BENEFICIARY ACCORDINGLY UNDER INTIMATION TO US."),
    ]
    flow.extend(_tag_lines(pairs))

    # Applicant tax-ID footer (regulatory-shape; varies by corridor)
    flow.append(Spacer(1, 10))
    flow.append(Paragraph("Applicant regulatory identifiers", _STYLE_SECTION))
    tax_rows = [["ID Type", "Value"]] + [[t, v] for t, v in c["applicant_tax_ids"]]
    t = Table(tax_rows, colWidths=[50 * mm, 127 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(t)
    return flow


def render_lc(corridor: Dict[str, Any], mode: str, out: Path) -> None:
    mode = mode.upper()
    if mode not in {"DRAFT_CLEAN", "DRAFT_RISKY", "SHIPMENT_CLEAN"}:
        raise ValueError(f"Unknown LC mode: {mode}")
    effective_corridor = _apply_risky_mods(corridor) if mode == "DRAFT_RISKY" else corridor
    doc = _doc(out, f"LC {effective_corridor['lc_number']}")
    doc.build(_lc_flow(effective_corridor, mode))


# --------------------------------------------------------------------------
# Invoice renderer
# --------------------------------------------------------------------------

def render_invoice(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Commercial Invoice {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("COMMERCIAL INVOICE", _STYLE_TITLE))
    flow.append(Spacer(1, 4))

    header_pairs = [
        ("Invoice No.", c["invoice_number"]),
        ("Invoice Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Proforma Reference", c["proforma_reference"]),
        ("Incoterms", c["incoterm"]),
        ("Currency", c["currency"]),
    ]
    flow.extend(_field_lines(header_pairs))
    flow.append(Spacer(1, 6))

    flow.append(Paragraph("Seller (Beneficiary)", _STYLE_SECTION))
    flow.append(Paragraph(
        f"{c['beneficiary_name']}<br/>{c['beneficiary_address']}",
        _STYLE_BODY,
    ))
    flow.append(Paragraph("Buyer (Applicant)", _STYLE_SECTION))
    tax_line = ", ".join([f"{t}: {v}" for t, v in c["applicant_tax_ids"]])
    flow.append(Paragraph(
        f"{c['applicant_name']}<br/>{c['applicant_address']}<br/>{tax_line}",
        _STYLE_BODY,
    ))

    flow.append(Paragraph("Line items", _STYLE_SECTION))
    rows: List[List[str]] = [["#", "Description", "HS Code", "Qty", "Unit", "Unit Price", "Line Amount"]]
    total = Decimal("0")
    for i, item in enumerate(c["goods_line_items"], 1):
        line = _line_amount(item)
        total += line
        rows.append([
            str(i),
            item["description"],
            item["hs"],
            f"{item['qty']:,}",
            item["unit"],
            f"{c['currency']} {_fmt_amount(item['unit_price'])}",
            f"{c['currency']} {_fmt_amount(line)}",
        ])
    rows.append(["", "", "", "", "", "TOTAL", f"{c['currency']} {_fmt_amount(total)}"])
    t = Table(rows, colWidths=[8 * mm, 55 * mm, 20 * mm, 18 * mm, 14 * mm, 30 * mm, 32 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 1), (6, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(t)

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        f"We hereby certify that the goods described above are of "
        f"{c['origin_country']} origin, brand new, free from any manufacturing "
        f"defect, and comply with the terms of LC No. {c['lc_number']}.",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Signature for Beneficiary", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["beneficiary_name"], _STYLE_BODY))

    doc.build(flow)


# --------------------------------------------------------------------------
# Bill of Lading renderer
# --------------------------------------------------------------------------

def render_bill_of_lading(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Bill of Lading {c['bl_number']}")
    flow: List = []

    flow.append(Paragraph("BILL OF LADING", _STYLE_TITLE))
    flow.append(Paragraph("Shipped on Board — Clean", _STYLE_SECTION))
    flow.append(Spacer(1, 4))

    header_pairs = [
        ("B/L No.", c["bl_number"]),
        ("Date of Issue (On Board)", c["issue_date"]),
        # Carrier name + full set of originals are UCP600 Art 20(a)(i)
        # and 20(a)(iv) requirements — a realistic clean BL must carry
        # both. Their absence made exporter_presentation correctly flag
        # bl.carrier_name / bl.original_set missing on the corpus
        # (2026-06-13).
        ("Carrier", c["carrier_name"]),
        ("No. of Original B/L", "THREE (3) ORIGINALS"),
        ("Vessel / Voyage", f"{c['vessel_name']} / {c['voyage_number']}"),
        ("Port of Loading", c["port_loading"]),
        ("Port of Discharge", c["port_discharge"]),
        ("Place of Delivery", c["final_destination"]),
        ("Freight Term", "FREIGHT PREPAID" if "CIF" in c["incoterm"] or "CFR" in c["incoterm"] or "CPT" in c["incoterm"] or "CIP" in c["incoterm"] else "FREIGHT COLLECT"),
        ("LC Reference", c["lc_number"]),
    ]
    flow.extend(_field_lines(header_pairs))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("Shipper", _STYLE_SECTION))
    flow.append(Paragraph(f"{c['beneficiary_name']}<br/>{c['beneficiary_address']}", _STYLE_BODY))
    flow.append(Paragraph("Consignee", _STYLE_SECTION))
    flow.append(Paragraph(
        f"TO ORDER OF {c['issuing_bank_name']}<br/>{c['issuing_bank_address']}",
        _STYLE_BODY,
    ))
    flow.append(Paragraph("Notify Party", _STYLE_SECTION))
    flow.append(Paragraph(f"{c['applicant_name']}<br/>{c['applicant_address']}", _STYLE_BODY))

    flow.append(Paragraph("Container / Seal", _STYLE_SECTION))
    rows = [["Container No.", "Seal No."]]
    for i, cn in enumerate(c["container_numbers"]):
        seal = c["seal_numbers"][i] if i < len(c["seal_numbers"]) else ""
        rows.append([cn, seal])
    t = Table(rows, colWidths=[60 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    flow.append(t)

    flow.append(Paragraph("Particulars furnished by the shipper", _STYLE_SECTION))
    total_qty = sum(i["qty"] for i in c["goods_line_items"])
    # Labeled field lines FIRST — real BLs carry a "No. of Packages" box,
    # and the vision extractor reliably transcribes labeled fields while
    # it only sometimes captures counts embedded in prose (live run
    # variance: bl.number_of_packages (missing) fired on BD-CN whenever
    # the prose line was skipped).
    flow.extend(_field_lines([
        ("Number of Packages", f"{_total_cartons(c['goods_line_items'])} cartons"),
        ("Total Quantity", f"{total_qty:,} pcs"),
    ]))
    total_cartons = _total_cartons(c["goods_line_items"])
    gw = round(total_qty * 0.7, 2)
    nw = round(total_qty * 0.6, 2)
    flow.append(Paragraph(
        f"{total_cartons:,} packages (cartons) containing {total_qty:,} pcs of "
        f"{c['goods_description']} — "
        f"Gross Weight: {gw:,} KGS — Net Weight: {nw:,} KGS",
        _STYLE_BODY,
    ))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "SHIPPED on board the vessel in apparent good order and "
        "condition. This Bill of Lading is clean and carries no notation "
        "of damage, defect, or loss.",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph("For the Carrier", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph("Master / Authorized Agent", _STYLE_BODY))

    doc.build(flow)


# --------------------------------------------------------------------------
# Packing list renderer
# --------------------------------------------------------------------------

def render_packing_list(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Packing List {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("PACKING LIST", _STYLE_TITLE))
    flow.append(Spacer(1, 4))

    header_pairs = [
        ("Invoice Reference", c["invoice_number"]),
        ("LC Reference", c["lc_number"]),
        ("Buyer", c["applicant_name"]),
        ("Seller", c["beneficiary_name"]),
        ("Shipment", f"{c['vessel_name']} voyage {c['voyage_number']}"),
    ]
    flow.extend(_field_lines(header_pairs))
    flow.append(Spacer(1, 6))

    flow.append(Paragraph("Carton-wise breakdown", _STYLE_SECTION))
    rows = [["Ctn From", "Ctn To", "Description", "Qty per Ctn", "Qty Total", "G.W. / Ctn", "N.W. / Ctn"]]
    ctn_start = 1
    for item in c["goods_line_items"]:
        qty = item["qty"]
        ctns = _cartons_for(qty)
        per_ctn = qty // ctns
        gw = round(per_ctn * 0.65, 2)
        nw = round(per_ctn * 0.55, 2)
        rows.append([
            str(ctn_start),
            str(ctn_start + ctns - 1),
            item["description"],
            f"{per_ctn:,}",
            f"{qty:,}",
            f"{gw} KG",
            f"{nw} KG",
        ])
        ctn_start += ctns
    t = Table(rows, colWidths=[18 * mm, 18 * mm, 55 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 1), (1, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
    ]))
    flow.append(t)

    flow.append(Spacer(1, 8))
    flow.append(Paragraph(
        f"Total packages: {ctn_start - 1} cartons. "
        f"All cartons marked with applicant name, purchase-order reference, "
        f"and country of origin: {c['origin_country']}.",
        _STYLE_BODY,
    ))
    # Cross-reference the BL's container/seal allocation. A real clean
    # packing list shows which cartons went into which container; without
    # this line SHIPMENT_CLEAN sets fail the PL↔BL container and seal
    # cross-checks (live CROSSDOC-CONTAINER-1/2, 2026-06-12) — the
    # "clean" corpus was structurally incapable of passing them.
    flow.append(Paragraph(
        "Container / Seal allocation: " + "; ".join(
            f"Container {cn} (Seal {c['seal_numbers'][i] if i < len(c['seal_numbers']) else 'N/A'})"
            for i, cn in enumerate(c["container_numbers"])
        ) + f" — cartons 1-{ctn_start - 1} stuffed across "
        f"{len(c['container_numbers'])} container(s).",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Signature for Beneficiary", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["beneficiary_name"], _STYLE_BODY))

    doc.build(flow)


# --------------------------------------------------------------------------
# Certificate of Origin renderer
# --------------------------------------------------------------------------

def render_certificate_of_origin(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Certificate of Origin {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("CERTIFICATE OF ORIGIN", _STYLE_TITLE))
    flow.append(Paragraph(c["chamber_of_commerce"], _STYLE_SECTION))
    flow.append(Spacer(1, 6))

    pairs = [
        ("Certificate No.", f"CO-{c['invoice_number']}"),
        ("Issue Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Invoice Reference", c["invoice_number"]),
        ("Exporter", f"{c['beneficiary_name']}, {c['beneficiary_address']}"),
        ("Consignee", f"{c['applicant_name']}, {c['applicant_address']}"),
        ("Country of Origin", c["origin_country"]),
        ("Country of Destination", c["port_discharge"].split(",")[-1].strip()),
        ("Means of Transport", f"Vessel {c['vessel_name']} voyage {c['voyage_number']}"),
    ]
    flow.extend(_field_lines(pairs))

    flow.append(Paragraph("Goods description and HS classification", _STYLE_SECTION))
    rows = [["Description", "HS Code", "Quantity"]]
    for item in c["goods_line_items"]:
        rows.append([item["description"], item["hs"], f"{item['qty']:,} {item['unit']}"])
    t = Table(rows, colWidths=[95 * mm, 30 * mm, 52 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    flow.append(t)

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        f"The undersigned authority hereby certifies that the goods "
        f"described above are of {c['origin_country']} origin as per "
        f"the records and documents submitted by the exporter.",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Officer", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["chamber_of_commerce"], _STYLE_BODY))

    doc.build(flow)


# --------------------------------------------------------------------------
# Insurance certificate renderer
# --------------------------------------------------------------------------

def render_insurance_certificate(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Insurance Certificate {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("MARINE CARGO INSURANCE CERTIFICATE", _STYLE_TITLE))
    flow.append(Paragraph(f"Cover mode: {c['insurance_cover_mode']}", _STYLE_SECTION))
    flow.append(Spacer(1, 4))

    cif_total = _total_amount(c["goods_line_items"])
    insured_amount = cif_total * Decimal("1.10")

    pairs = [
        ("Certificate No.", f"INS-{c['invoice_number']}"),
        ("Issue Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Insured Party",
         c["applicant_name"] if "APPLICANT" in c["insurance_cover_mode"].upper()
         else c["beneficiary_name"]),
        ("Sum Insured",
         f"{c['currency']} {_fmt_amount(insured_amount)} "
         f"(110 percent of invoice value)"),
        ("Cover", "Institute Cargo Clauses (A) + Institute War Clauses (Cargo) + Institute Strikes Clauses (Cargo)"),
        ("From", c["port_loading"]),
        ("To", c["port_discharge"]),
        ("Vessel / Voyage", f"{c['vessel_name']} / {c['voyage_number']}"),
        ("Claims Payable At", c["final_destination"]),
    ]
    flow.extend(_field_lines(pairs))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "We certify that insurance covering the goods described above "
        "has been effected in accordance with the Institute Cargo Clauses "
        "as indicated, and is endorsed in blank as required by the "
        "underlying Letter of Credit.",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Signature", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))

    doc.build(flow)


# --------------------------------------------------------------------------
# Inspection certificate renderer
# --------------------------------------------------------------------------

def render_beneficiary_certificate(c: Dict[str, Any], out: Path) -> None:
    """Render the Beneficiary Certificate when the LC's 46A asks for one.

    The certificate is a corridor-driven attestation by the seller. The
    actual statement is set per corridor in `beneficiary_certificate_statement`
    and matches the corresponding 46A clause text.
    """
    statement = c.get("beneficiary_certificate_statement")
    if not statement:
        raise ValueError(
            "render_beneficiary_certificate called for a corridor whose "
            "LC does not require a Beneficiary Certificate. Caller should "
            "gate on `c.get('beneficiary_certificate_statement')`."
        )
    doc = _doc(out, f"Beneficiary Certificate {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("BENEFICIARY CERTIFICATE", _STYLE_TITLE))
    flow.append(Paragraph(c["beneficiary_name"], _STYLE_SECTION))
    flow.append(Spacer(1, 4))

    pairs = [
        ("Certificate No.", f"BC-{c['invoice_number']}"),
        ("Issue Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Invoice Reference", c["invoice_number"]),
        ("Beneficiary", f"{c['beneficiary_name']}, {c['beneficiary_address']}"),
        ("Applicant", f"{c['applicant_name']}, {c['applicant_address']}"),
        ("Country of Origin", c["origin_country"]),
    ]
    flow.extend(_field_lines(pairs))
    flow.append(Spacer(1, 8))

    flow.append(Paragraph("Statement", _STYLE_SECTION))
    flow.append(Paragraph(
        f"We, {c['beneficiary_name']}, hereby certify that the goods "
        f"shipped under Letter of Credit No. {c['lc_number']} and Invoice "
        f"No. {c['invoice_number']} satisfy the following condition "
        f"required under LC clause 46A:",
        _STYLE_BODY,
    ))
    flow.append(Spacer(1, 4))
    flow.append(Paragraph(
        f"<i>{statement}</i>",
        _STYLE_BODY,
    ))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Signature for Beneficiary", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["beneficiary_name"], _STYLE_BODY))

    doc.build(flow)


def render_fumigation_certificate(c: Dict[str, Any], out: Path) -> None:
    """Render the Fumigation / ISPM 15 Certificate when the LC asks for it.

    Required for shipments with wood packaging (ISPM 15 compliance). The
    fumigation provider and treatment text are corridor-driven; the
    renderer raises if called for a corridor that doesn't define them.
    """
    provider = c.get("fumigation_provider")
    treatment = c.get("fumigation_treatment")
    if not provider or not treatment:
        raise ValueError(
            "render_fumigation_certificate called for a corridor whose "
            "LC does not require a Fumigation Certificate. Caller should "
            "gate on `c.get('fumigation_provider')`."
        )
    doc = _doc(out, f"Fumigation Certificate {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("FUMIGATION CERTIFICATE", _STYLE_TITLE))
    flow.append(Paragraph("ISPM 15 Compliant — Wood Packaging Material", _STYLE_SECTION))
    flow.append(Spacer(1, 4))

    pairs = [
        ("Certificate No.", f"FUM-{c['invoice_number']}"),
        ("Treatment Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Invoice Reference", c["invoice_number"]),
        ("Shipper", c["beneficiary_name"]),
        ("Consignee", c["applicant_name"]),
        ("Vessel / Voyage", f"{c['vessel_name']} / {c['voyage_number']}"),
        ("Port of Loading", c["port_loading"]),
        ("Port of Discharge", c["port_discharge"]),
        ("Container No.", ", ".join(c.get("container_numbers") or []) or "N/A"),
        ("Treatment Provider", provider),
    ]
    flow.extend(_field_lines(pairs))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph("Treatment", _STYLE_SECTION))
    flow.append(Paragraph(treatment, _STYLE_BODY))

    flow.append(Paragraph("Statement", _STYLE_SECTION))
    flow.append(Paragraph(
        f"We hereby certify that all wood packaging material used in the "
        f"shipment described above has been treated in accordance with "
        f"ISPM 15 (International Standards for Phytosanitary Measures No. 15) "
        f"and bears the ISPM 15 mark applied by {provider}. The wood "
        f"packaging is free from bark and from live pests.",
        _STYLE_BODY,
    ))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Inspector", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(provider, _STYLE_BODY))

    doc.build(flow)


def render_draft_bill_of_exchange(c: Dict[str, Any], out: Path) -> None:
    """Render the Draft / Bill of Exchange that accompanies any sight LC.

    Even when 46A doesn't enumerate it, sight LCs (42C: SIGHT) carry an
    implicit draft drawn on the drawee bank for full invoice value. The
    draft is a corridor-agnostic financial instrument; data comes from
    existing corridor fields (currency, drawee, beneficiary, amount).
    """
    from decimal import Decimal as _Decimal

    line_sum = sum(
        _Decimal(str(i["qty"])) * _Decimal(str(i["unit_price"]))
        for i in c.get("goods_line_items") or []
    )
    drawee_bank = c.get("issuing_bank_name") or c.get("drawee_bic", "")
    drawee_address = c.get("issuing_bank_address") or ""

    doc = _doc(out, f"Draft Bill of Exchange {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("BILL OF EXCHANGE", _STYLE_TITLE))
    flow.append(Paragraph(
        "Sight Draft — Negotiable Instrument under LC Negotiation",
        _STYLE_SECTION,
    ))
    flow.append(Spacer(1, 6))

    pairs = [
        ("Bill of Exchange No.", f"BOE-{c['lc_number']}"),
        ("Date of Draft", c["issue_date"]),
        ("Place of Draft", c["beneficiary_address"].split(",")[-1].strip()),
        ("LC Reference", c["lc_number"]),
        ("Currency", c["currency"]),
        ("Amount", f"{c['currency']} {_fmt_amount(line_sum)}"),
        ("Tenor", "AT SIGHT"),
        ("Drawer", f"{c['beneficiary_name']}, {c['beneficiary_address']}"),
        ("Drawee", f"{drawee_bank} — BIC {c.get('drawee_bic', '')}"),
        ("Payable To", "ORDER OF DRAWER (or as endorsed)"),
    ]
    flow.extend(_field_lines(pairs))

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        f"AT SIGHT, pay against this First of Exchange (Second of the same "
        f"tenor and date being unpaid) to the order of {c['beneficiary_name']} "
        f"the sum of {c['currency']} {_fmt_amount(line_sum)} "
        f"({_amount_words(line_sum, c['currency'])}) for value received and "
        f"charge the same to the account of {c['applicant_name']} as per "
        f"Letter of Credit No. {c['lc_number']} issued by {drawee_bank}.",
        _STYLE_BODY,
    ))

    flow.append(Spacer(1, 8))
    flow.append(Paragraph("To:", _STYLE_BODY))
    flow.append(Paragraph(drawee_bank, _STYLE_BODY))
    if drawee_address:
        flow.append(Paragraph(drawee_address, _STYLE_BODY))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph("For and on behalf of the Drawer:", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["beneficiary_name"], _STYLE_BODY))

    doc.build(flow)


def _amount_words(amount: Any, currency: str) -> str:
    """Render an amount as 'words ONLY' suffix used on bills of exchange.

    Numeric-precise English-style words are out of scope for synthetic
    fixture output; we render an unambiguous bracketed numeric form
    that tooling parses consistently.
    """
    from decimal import Decimal as _Decimal
    val = _Decimal(str(amount))
    return f"{currency} {val:,.2f} ONLY"


def render_inspection_certificate(c: Dict[str, Any], out: Path) -> None:
    doc = _doc(out, f"Inspection Certificate {c['invoice_number']}")
    flow: List = []

    flow.append(Paragraph("CERTIFICATE OF INSPECTION", _STYLE_TITLE))
    flow.append(Paragraph(c["inspection_body"], _STYLE_SECTION))
    flow.append(Spacer(1, 4))

    pairs = [
        ("Certificate No.", f"INSP-{c['invoice_number']}"),
        ("Inspection Date", c["issue_date"]),
        ("LC Reference", c["lc_number"]),
        ("Shipper", c["beneficiary_name"]),
        ("Consignee", c["applicant_name"]),
        ("Goods Description", c["goods_description"].split(".")[0]),
        ("Country of Origin", c["origin_country"]),
        ("Language Used", c["language"]),
    ]
    flow.extend(_field_lines(pairs))

    flow.append(Paragraph("Findings", _STYLE_SECTION))
    flow.append(Paragraph(
        "Goods were inspected at the beneficiary's premises prior to "
        "shipment. The inspected quantity, quality, packing, and marking "
        "conform to the specifications set out in the Letter of Credit "
        "and Proforma Invoice. All packages are marked with country of "
        "origin in indelible ink. Goods are brand new, free from "
        "manufacturing defects.",
        _STYLE_BODY,
    ))

    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Authorized Inspector", _STYLE_BODY))
    flow.append(Paragraph("______________________________", _STYLE_BODY))
    flow.append(Paragraph(c["inspection_body"], _STYLE_BODY))

    doc.build(flow)
