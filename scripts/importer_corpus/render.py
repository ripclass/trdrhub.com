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


def _tag_pairs(pairs: List[tuple[str, str]]) -> Table:
    """Render [tag, value] pairs as a 2-column table in MT700 style."""
    data = []
    for tag, val in pairs:
        data.append([
            Paragraph(tag, _STYLE_TAG),
            Paragraph(val, _STYLE_TAG_VAL),
        ])
    tbl = Table(data, colWidths=[32 * mm, 145 * mm])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return tbl


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
        ("27 Sequence of Total", "1/1"),
        ("40A Form of Documentary Credit", "IRREVOCABLE"),
        ("20 Documentary Credit Number", c["lc_number"]),
        ("31C Date of Issue", _mt700_date(c["issue_date"])),
        ("40E Applicable Rules", c["applicable_rules"]),
        ("31D Date and Place of Expiry", f"{_mt700_date(c['expiry_date'])} {c['expiry_place']}"),
        ("50 Applicant", f"{c['applicant_name']}<br/>{c['applicant_address']}"),
        ("59 Beneficiary", f"{c['beneficiary_account_hint']}<br/>{c['beneficiary_name']}<br/>{c['beneficiary_address']}"),
        ("32B Currency Code, Amount", f"{c['currency']} {c['amount']}"),
        ("41D Available With ... By ...", c["available_with"]),
        ("42C Drafts at ...", "SIGHT"),
        ("42A Drawee", c["drawee_bic"]),
        ("43P Partial Shipments", c["partial_shipments"]),
        ("43T Transhipment", c["transhipment"]),
        ("44E Port of Loading/Airport of Departure", c["port_loading"]),
        ("44F Port of Discharge/Airport of Destination", c["port_discharge"]),
        ("44B Place of Final Destination/For Transportation to .../Place of Delivery", c["final_destination"]),
        ("44C Latest Date of Shipment", _mt700_date(c["latest_shipment_date"])),
        ("45A Description of Goods and/or Services", c["goods_description"]),
        (
            "46A Documents Required",
            "<br/><br/>".join(c["documents_required"]),
        ),
        (
            "47A Additional Conditions",
            "<br/><br/>".join(c["additional_conditions"]),
        ),
        ("71D Charges", c["charges_clause"]),
        (
            "48 Period for Presentation in Days",
            f"{c['presentation_period_days']}/FROM SHIPMENT BUT WITHIN LC EXPIRY",
        ),
        ("49 Confirmation Instructions", c["confirmation"]),
        ("78 Instructions to the Paying/Accepting/Negotiating Bank", c["instructions_78"]),
        ("57A 'Advise Through' Bank", c["advise_through_bic"]),
        ("72Z Sender to Receiver Information", "PLS ADVISE THE CREDIT TO THE BENEFICIARY ACCORDINGLY UNDER INTIMATION TO US."),
    ]
    flow.append(_tag_pairs(pairs))

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
    htbl = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in header_pairs],
        colWidths=[40 * mm, 137 * mm],
    )
    htbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    flow.append(htbl)
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
        ("Vessel / Voyage", f"{c['vessel_name']} / {c['voyage_number']}"),
        ("Port of Loading", c["port_loading"]),
        ("Port of Discharge", c["port_discharge"]),
        ("Place of Delivery", c["final_destination"]),
        ("Freight Term", "FREIGHT PREPAID" if "CIF" in c["incoterm"] or "CFR" in c["incoterm"] or "CPT" in c["incoterm"] or "CIP" in c["incoterm"] else "FREIGHT COLLECT"),
        ("LC Reference", c["lc_number"]),
    ]
    t = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in header_pairs],
        colWidths=[48 * mm, 129 * mm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(t)
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
    gw = round(total_qty * 0.7, 2)
    nw = round(total_qty * 0.6, 2)
    flow.append(Paragraph(
        f"{total_qty:,} packages containing {c['goods_description']} — "
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
    t = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in header_pairs],
        colWidths=[48 * mm, 129 * mm],
    )
    flow.append(t)
    flow.append(Spacer(1, 6))

    flow.append(Paragraph("Carton-wise breakdown", _STYLE_SECTION))
    rows = [["Ctn From", "Ctn To", "Description", "Qty per Ctn", "Qty Total", "G.W. / Ctn", "N.W. / Ctn"]]
    ctn_start = 1
    for item in c["goods_line_items"]:
        qty = item["qty"]
        ctns = max(1, qty // 100)
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
    t = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in pairs],
        colWidths=[48 * mm, 129 * mm],
    )
    flow.append(t)

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
    t = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in pairs],
        colWidths=[48 * mm, 129 * mm],
    )
    flow.append(t)

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
    t = Table(
        [[Paragraph(k, _STYLE_TAG), Paragraph(v, _STYLE_TAG_VAL)] for k, v in pairs],
        colWidths=[48 * mm, 129 * mm],
    )
    flow.append(t)

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
