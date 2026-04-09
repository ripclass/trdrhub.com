"""Canonical LC document model.

Defines the format-agnostic shape that every LC extractor in the codebase
should produce. The validation pipeline reads from this shape, NOT from
whatever flavor of dict the upstream parser happened to emit.

Why this exists
---------------
Today the codebase has at least four LC extractors:

1. `multimodal_document_extractor.py`  -- vision LLM (primary)
2. `swift_mt700_full.py`               -- regex MT700 parser (currently orphaned)
3. `iso20022_lc_extractor.py`          -- ISO 20022 tsmt XML parser
4. `ai_first_extractor.py`             -- text-AI fallback

Each of them produces a slightly different dict shape. The vision LLM uses
`lc_number` while the regex MT700 parser uses `reference`. Amount comes back
as a scalar, a `{value, currency}` dict, or a `credit_amount` dict depending
on which path you hit. The ISO 20022 parser nests applicants/beneficiaries
into structured `{name, address, country, bic}` dicts whereas everyone else
uses bare strings. (See the audit report from 2026-04-08 for details.)

`LCDocument` collapses all of that into ONE Pydantic model. Each extractor
gets a `from_xxx()` classmethod that adapts its native output. Downstream
code (validation, presentation, required-fields derivation) reads from a
single canonical shape.

Field naming follows the SWIFT MT700 spec exactly (see comments). When you
need a "format-agnostic" name, use the field name in this model.

Backwards-compat strategy
-------------------------
Downstream code today reads from a free-form `lc_context` dict with keys
like `lc_number`, `applicant`, `amount`, `currency`, etc. The `to_lc_context()`
method on this model produces that exact dict shape so downstream consumers
keep working without changes.

If you ever want to make a downstream consumer typed, swap its
`lc_context: dict` argument for `lc: LCDocument`. Both APIs will coexist
during the migration.
"""

from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class LCAddress(BaseModel):
    """A postal address.

    ISO 20022 messages give us this structured shape. SWIFT MT700 messages
    give us a flat 4-line, 35-char-per-line text blob, which we collapse into
    `raw` until/unless someone parses it further.
    """
    model_config = ConfigDict(extra="allow")

    raw: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None  # ISO 3166-1 alpha-2

    def to_string(self) -> str:
        """Render as a single string for legacy consumers that expect text."""
        if self.raw:
            return self.raw
        parts = [self.street, self.city, self.region, self.postal_code, self.country]
        return ", ".join(p for p in parts if p)


class LCParty(BaseModel):
    """A party on the LC — applicant, beneficiary, issuing bank, etc.

    SWIFT MT700 fields 50, 59, 52a, 57a all map here.
    ISO 20022 messages give this directly as `<Applcnt>`, `<Bnfcry>`, etc.
    with separate `<Nm>` and `<PstlAdr>` elements.
    """
    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    address: Optional[LCAddress] = None
    bic: Optional[str] = None  # SWIFT BIC code (e.g. ICBKCNBJ400) when known
    country_code: Optional[str] = None

    def to_string(self) -> str:
        """Legacy `applicant: str` shape — collapse to a single string."""
        if not self.name and not self.address:
            return ""
        addr = self.address.to_string() if self.address else ""
        if self.name and addr:
            return f"{self.name}\n{addr}"
        return self.name or addr or ""


class LCAmount(BaseModel):
    """A monetary amount with its currency. Maps to MT700 Field 32B."""
    model_config = ConfigDict(extra="allow")

    value: Optional[Decimal] = None
    currency: Optional[str] = None  # ISO 4217 3-letter code

    def to_pair(self) -> Dict[str, Any]:
        return {"value": float(self.value) if self.value is not None else None, "currency": self.currency}


class LCExpiry(BaseModel):
    """MT700 Field 31D — date and place of expiry combined."""
    model_config = ConfigDict(extra="allow")

    date: Optional[date_type] = None
    place: Optional[str] = None


class LCAvailability(BaseModel):
    """MT700 Field 41a — Available With / Available By.

    Tells us where documents must be presented and HOW the credit is
    available (payment / acceptance / negotiation / deferred payment).
    Determines the payment mechanism for the LC.
    """
    model_config = ConfigDict(extra="allow")

    available_with: Optional[str] = None  # bank name or "ANY BANK"
    available_with_bic: Optional[str] = None
    available_by: Optional[str] = None    # PAYMENT / ACCEPTANCE / NEGOTIATION / DEFERRED


class LCDrafts(BaseModel):
    """MT700 Field 42C (Drafts at) + Field 42a (Drawee)."""
    model_config = ConfigDict(extra="allow")

    drafts_at: Optional[str] = None  # tenor: "AT SIGHT" / "30 DAYS FROM B/L DATE" / etc.
    drawee: Optional[str] = None     # who the draft is drawn on
    drawee_bic: Optional[str] = None


class LCDocumentRequirement(BaseModel):
    """One entry from MT700 Field 46A "Documents Required".

    Each clause typically reads like:
        "FULL SET OF CLEAN ON-BOARD BILL OF LADING ... BL TO SHOW VESSEL
        NAME, VOYAGE NO., CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT."

    `raw_text` carries the unprocessed clause. `document_type` carries the
    canonicalized doc type (commercial_invoice, bill_of_lading, etc.) when
    we can detect one. `field_requirements` carries the per-doc fields the
    clause says must appear.
    """
    model_config = ConfigDict(extra="allow")

    raw_text: str
    document_type: Optional[str] = None
    field_requirements: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# The canonical LC document
# ---------------------------------------------------------------------------


class LCDocument(BaseModel):
    """Format-agnostic canonical Letter of Credit.

    All field names follow the SWIFT MT700 spec (see inline comments). Every
    extractor in the codebase should produce one of these via the relevant
    `from_xxx()` classmethod.

    Required-by-the-spec mandatory fields:
      Field 27, 40A, 20, 31C, 31D (date+place), 50, 59, 32B, 41a, 44E, 44F,
      44C, 45A, 46A, 47A, 48, 40E

    Important-optional fields the engine should still parse when present:
      Field 39A, 43P, 43T, 42C/42a, 49, 78, 71D
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    # ----- MT700 mandatory -----
    sequence_of_total: Optional[str] = None         # Field 27 — e.g. "1/1"
    form_of_documentary_credit: Optional[str] = None  # Field 40A
    lc_number: Optional[str] = None                 # Field 20
    issue_date: Optional[date_type] = None           # Field 31C
    expiry: Optional[LCExpiry] = None               # Field 31D
    applicable_rules: Optional[str] = None          # Field 40E (UCP600 / EUCP / ISP / URDG)
    applicant: Optional[LCParty] = None             # Field 50
    beneficiary: Optional[LCParty] = None           # Field 59
    amount: Optional[LCAmount] = None               # Field 32B
    availability: Optional[LCAvailability] = None   # Field 41a
    port_of_loading: Optional[str] = None           # Field 44E
    port_of_discharge: Optional[str] = None         # Field 44F
    latest_shipment_date: Optional[date_type] = None  # Field 44C
    goods_description: Optional[str] = None         # Field 45A
    documents_required: List[LCDocumentRequirement] = Field(default_factory=list)  # Field 46A
    additional_conditions: List[str] = Field(default_factory=list)  # Field 47A
    period_for_presentation_days: Optional[int] = None  # Field 48

    # ----- MT700 important-optional -----
    amount_tolerance_percent: Optional[Decimal] = None  # Field 39A — "ABOUT" / ±%
    partial_shipments: Optional[str] = None         # Field 43P — ALLOWED / NOT ALLOWED / CONDITIONAL
    transshipment: Optional[str] = None             # Field 43T
    drafts: Optional[LCDrafts] = None               # Field 42C + 42a
    confirmation_instructions: Optional[str] = None  # Field 49 — CONFIRM / MAY ADD / WITHOUT
    instructions_to_paying_bank: Optional[str] = None  # Field 78
    charges: Optional[str] = None                   # Field 71D

    # ----- Auxiliary parties extracted from various optional fields -----
    issuing_bank: Optional[LCParty] = None          # from Field 52a or message header
    advising_bank: Optional[LCParty] = None         # from Field 57a
    confirming_bank: Optional[LCParty] = None       # inferred from Field 49 / others

    # ----- Lineage / provenance -----
    source_format: Optional[str] = None  # "vision_llm" / "swift_mt700" / "iso20022" / "ai_first_text" / "legacy_dict"
    source_message_type: Optional[str] = None  # "MT700" / "tsmt.019" / etc.
    extraction_method: Optional[str] = None  # provider:model when available
    extraction_confidence: Optional[float] = None
    raw_field_dict: Optional[Dict[str, Any]] = None  # original parser output, for debugging

    # =======================================================================
    # Constructors — adapters for each existing extractor
    # =======================================================================

    @classmethod
    def from_iso20022(cls, payload: Dict[str, Any]) -> "LCDocument":
        """Build an LCDocument from `iso20022_lc_extractor.extract_iso20022_lc_enhanced()`
        output (and the async `extract_iso20022_with_ai_fallback` wrapper).

        The ISO 20022 extractor returns a flat-ish dict with some nested
        structures. Expected keys (post-step-3 when all mandatory fields
        are populated):

            {
              "format": "iso20022",
              "schema": "tsmt.014" | "tsrv.001" | ...,
              "_detection_confidence": 0.95,
              "_extraction_confidence": 0.9,
              "_extraction_method": "iso20022_xml",
              "number": "EXP2026BD001",
              "sequence_of_total": "1/1",                 # NEW (Field 27)
              "form_of_doc_credit": "IRREVOCABLE",
              "applicable_rules": "UCP600",               # NEW (Field 40E)
              "issue_date": "2026-04-15",                 # NEW (Field 31C)
              "period_for_presentation": 21,              # NEW (Field 48)
              "additional_conditions": [                  # NEW (Field 47A)
                "DOCUMENTS MUST BE IN ENGLISH.",
                "INSURANCE MUST COVER 110% ...",
              ],
              "available_with": {                         # NEW (Field 41a)
                "name": "ICBC USA",
                "bic": "ICBKUS33XXX",
                ...
              },
              "available_by": "NEGOTIATION",              # NEW (Field 41a)
              "amount": {"value": 458750.0, "currency": "USD"},
              "currency": "USD",
              "applicant": {"name": ..., "address": {...}, "bic": ...},
              "beneficiary": {"name": ..., "address": {...}, "bic": ...},
              "issuing_bank": {"name": ..., "bic": ...},
              "advising_bank": {"name": ..., "bic": ...},
              "dates": {
                "expiry": "2026-10-15",
                "place_of_expiry": "NEW YORK",
                "latest_shipment": "2026-09-30",
                "issue_date": "2026-04-15",
                "issue_place": "NEW YORK",
              },
              "ports": {"loading": "...", "discharge": "..."},
              "goods_description": "...",
              "documents_required": [...],
              "partial_shipments": "ALLOWED",
              "transshipment": "NOT ALLOWED",
              "incoterm": "FOB",
            }
        """
        if not isinstance(payload, dict):
            payload = {}

        dates_block = payload.get("dates") if isinstance(payload.get("dates"), dict) else {}
        ports_block = payload.get("ports") if isinstance(payload.get("ports"), dict) else {}

        # Expiry — ISO 20022 nests under `dates`.
        expiry: Optional[LCExpiry] = None
        expiry_date_value = _coerce_date(dates_block.get("expiry"))
        expiry_place_value = _str_or_none(dates_block.get("place_of_expiry"))
        if expiry_date_value is not None or expiry_place_value is not None:
            expiry = LCExpiry(date=expiry_date_value, place=expiry_place_value)

        # Amount — ISO 20022 nests under {"amount": {"value", "currency"}}.
        amount_value: Optional[LCAmount] = None
        amount_block = payload.get("amount")
        if isinstance(amount_block, dict):
            value = _coerce_decimal(amount_block.get("value") or amount_block.get("amount"))
            currency = _str_or_none(amount_block.get("currency") or payload.get("currency"))
            if value is not None or currency is not None:
                amount_value = LCAmount(value=value, currency=currency)
        elif amount_block is not None:
            value = _coerce_decimal(amount_block)
            currency = _str_or_none(payload.get("currency"))
            if value is not None or currency is not None:
                amount_value = LCAmount(value=value, currency=currency)

        # Availability — newly populated by _extract_mt700_mandatory_equivalents.
        availability: Optional[LCAvailability] = None
        avlbl_with_raw = payload.get("available_with")
        avlbl_by_raw = payload.get("available_by")
        if isinstance(avlbl_with_raw, dict):
            avlbl_with_name = _str_or_none(avlbl_with_raw.get("name"))
            avlbl_with_bic = _str_or_none(avlbl_with_raw.get("bic"))
            if avlbl_with_name or avlbl_with_bic or avlbl_by_raw:
                availability = LCAvailability(
                    available_with=avlbl_with_name,
                    available_with_bic=avlbl_with_bic,
                    available_by=_str_or_none(avlbl_by_raw),
                )
        elif avlbl_with_raw or avlbl_by_raw:
            availability = LCAvailability(
                available_with=_str_or_none(avlbl_with_raw),
                available_by=_str_or_none(avlbl_by_raw),
            )

        return cls(
            sequence_of_total=_str_or_none(payload.get("sequence_of_total")),
            form_of_documentary_credit=_str_or_none(
                payload.get("form_of_doc_credit") or payload.get("form_of_documentary_credit")
            ),
            lc_number=_str_or_none(payload.get("number") or payload.get("lc_number")),
            issue_date=_coerce_date(
                payload.get("issue_date") or dates_block.get("issue_date")
            ),
            expiry=expiry,
            applicable_rules=_str_or_none(payload.get("applicable_rules")),
            applicant=_build_party(payload.get("applicant")),
            beneficiary=_build_party(payload.get("beneficiary")),
            amount=amount_value,
            availability=availability,
            port_of_loading=_str_or_none(ports_block.get("loading") or payload.get("port_of_loading")),
            port_of_discharge=_str_or_none(ports_block.get("discharge") or payload.get("port_of_discharge")),
            latest_shipment_date=_coerce_date(
                dates_block.get("latest_shipment") or payload.get("latest_shipment_date")
            ),
            goods_description=_str_or_none(payload.get("goods_description")),
            documents_required=_build_documents_required(payload.get("documents_required")),
            additional_conditions=_coerce_string_list(payload.get("additional_conditions")),
            period_for_presentation_days=_coerce_int(
                payload.get("period_for_presentation_days")
                or payload.get("period_for_presentation")
            ),
            amount_tolerance_percent=_coerce_decimal(
                payload.get("amount_tolerance") or payload.get("tolerance")
            ),
            partial_shipments=_str_or_none(payload.get("partial_shipments")),
            transshipment=_str_or_none(payload.get("transshipment")),
            drafts=_build_drafts(payload),
            confirmation_instructions=_str_or_none(payload.get("confirmation_instructions")),
            instructions_to_paying_bank=_str_or_none(payload.get("instructions_to_paying_bank")),
            charges=_str_or_none(payload.get("charges")),
            issuing_bank=_build_party(payload.get("issuing_bank")),
            advising_bank=_build_party(payload.get("advising_bank")),
            confirming_bank=_build_party(payload.get("confirming_bank")),
            source_format="iso20022",
            source_message_type=_str_or_none(payload.get("schema")),
            extraction_method=_str_or_none(payload.get("_extraction_method") or "iso20022_xml"),
            extraction_confidence=_coerce_float(payload.get("_extraction_confidence")),
            raw_field_dict=dict(payload),
        )

    @classmethod
    def from_swift_mt700_full(cls, payload: Dict[str, Any]) -> "LCDocument":
        """Build an LCDocument from `swift_mt700_full.parse_mt700_full()` output.

        That parser returns a dict with shape::

            {
              "message_type": "MT700",
              "raw": {<tag>: <value>, ...},
              "blocks": {...},   # alias for raw
              "fields": {
                "reference": "EXP2026BD001",
                "sequence": "1/1",
                "form_of_doc_credit": "IRREVOCABLE",
                "applicable_rules": "UCP LATEST VERSION",
                "date_of_issue": "2026-04-15",  # already ISO-formatted
                "expiry_details": {
                    "expiry_place_and_date": "261015USA",
                    "expiry_date_iso": "2026-10-15",
                },
                "applicant": "GLOBAL IMPORTERS INC.\\n1250 HUDSON STREET...",
                "beneficiary": "DHAKA KNITWEAR...",
                "credit_amount": {"currency": "USD", "amount": 458750.0, "raw": "..."},
                "tolerance": "0",
                "available_with": {"by": "41A", "details": "ANY BANK IN USA\\nBY NEGOTIATION"},
                "shipment": {"drafts_at": "AT SIGHT", "drawee": None,
                             "partial_shipments": None, "transshipment": None},
                "period_for_presentation": "21 DAYS FROM SHIPMENT DATE",
                "shipment_details": {
                    "port_of_loading_airport_of_departure": "CHITTAGONG SEA PORT, BANGLADESH",
                    "port_of_discharge_airport_of_destination": "NEW YORK, USA",
                    "latest_date_of_shipment": "260930",  # still raw YYMMDD
                    ...
                },
                "description_of_goods": "GARMENTS FOR EXPORT MARKET...",
                "docs_required": ["SIGNED COMMERCIAL INVOICE ...", ...],
                "additional_conditions": [...],
                "charges": "ALL BANK CHARGES...",
                "reimbursing_bank": "...",
                "advising_bank": "...",
                "instructions_to_paying_accepting_negotiating_bank": "...",
              }
            }
        """
        if not isinstance(payload, dict):
            payload = {}
        fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        raw_blocks = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}

        # Expiry: Field 31D combines date + place ("261015USA" or
        # "261015 USA"). The parser's `expiry_date_iso` only works when the
        # date and place are whitespace-separated; for the glued form we
        # parse the leading 6 digits of `expiry_place_and_date` ourselves.
        expiry: Optional[LCExpiry] = None
        expiry_details = fields.get("expiry_details") if isinstance(fields.get("expiry_details"), dict) else {}
        if expiry_details:
            iso_date_value = _coerce_date(expiry_details.get("expiry_date_iso"))
            combined = str(expiry_details.get("expiry_place_and_date") or "")
            place_value: Optional[str] = None
            if len(combined) > 6 and combined[:6].isdigit():
                place_value = combined[6:].strip() or None
                if iso_date_value is None:
                    # Parser's own expiry_date_iso was None — recover from
                    # the glued "YYMMDD<place>" form.
                    iso_date_value = _coerce_date(combined[:6])
            # Also handle the space-separated form "261015 USA"
            if iso_date_value is None and combined:
                tokens = combined.split()
                if tokens:
                    iso_date_value = _coerce_date(tokens[0])
                    if place_value is None and len(tokens) > 1:
                        place_value = " ".join(tokens[1:]).strip() or None
            if iso_date_value is not None or place_value is not None:
                expiry = LCExpiry(date=iso_date_value, place=place_value)

        # Amount: credit_amount = {"currency", "amount", "raw"}
        amount_value: Optional[LCAmount] = None
        credit_amount = fields.get("credit_amount")
        if isinstance(credit_amount, dict):
            amount_scalar = _coerce_decimal(credit_amount.get("amount") or credit_amount.get("value"))
            amount_currency = _str_or_none(credit_amount.get("currency"))
            if amount_scalar is not None or amount_currency is not None:
                amount_value = LCAmount(value=amount_scalar, currency=amount_currency)

        # Available with / by: swift_mt700_full lumps them into one dict with
        # a `by` key that's actually the MT700 tag id (41A / 41D), not the
        # method. The `details` field holds the free-text bank name + method.
        availability: Optional[LCAvailability] = None
        avail_raw = fields.get("available_with")
        if isinstance(avail_raw, dict) and avail_raw.get("details"):
            details_text = str(avail_raw["details"])
            # Split on newline — first line is bank, second is method.
            lines = [ln.strip() for ln in details_text.splitlines() if ln.strip()]
            bank = lines[0] if lines else None
            method: Optional[str] = None
            for line in lines[1:]:
                upper = line.upper()
                if any(kw in upper for kw in ("NEGOTIATION", "PAYMENT", "ACCEPTANCE", "DEFERRED")):
                    method = line
                    break
            availability = LCAvailability(available_with=bank, available_by=method)

        # Drafts: swift_mt700_full nests under `shipment`.
        drafts: Optional[LCDrafts] = None
        shipment = fields.get("shipment") if isinstance(fields.get("shipment"), dict) else {}
        drafts_at_value = _str_or_none(shipment.get("drafts_at"))
        drawee_value = _str_or_none(shipment.get("drawee"))
        if drafts_at_value or drawee_value:
            drafts = LCDrafts(drafts_at=drafts_at_value, drawee=drawee_value)

        # Shipment details for ports + latest shipment date.
        shipment_details = (
            fields.get("shipment_details")
            if isinstance(fields.get("shipment_details"), dict)
            else {}
        )
        port_of_loading_value = _str_or_none(
            shipment_details.get("port_of_loading_airport_of_departure")
        )
        port_of_discharge_value = _str_or_none(
            shipment_details.get("port_of_discharge_airport_of_destination")
        )
        latest_shipment_date_value = _coerce_date(
            shipment_details.get("latest_date_of_shipment")
        )

        # Period for presentation: swift_mt700_full keeps the raw text
        # (e.g. "21 DAYS FROM SHIPMENT DATE"). Our _coerce_int pulls the
        # leading integer.
        period_days = _coerce_int(fields.get("period_for_presentation"))

        return cls(
            sequence_of_total=_str_or_none(fields.get("sequence")),
            form_of_documentary_credit=_str_or_none(fields.get("form_of_doc_credit")),
            lc_number=_str_or_none(fields.get("reference")),
            issue_date=_coerce_date(fields.get("date_of_issue")),
            expiry=expiry,
            applicable_rules=_str_or_none(fields.get("applicable_rules")),
            applicant=_build_party(fields.get("applicant")),
            beneficiary=_build_party(fields.get("beneficiary")),
            amount=amount_value,
            availability=availability,
            port_of_loading=port_of_loading_value,
            port_of_discharge=port_of_discharge_value,
            latest_shipment_date=latest_shipment_date_value,
            goods_description=_str_or_none(fields.get("description_of_goods")),
            documents_required=_build_documents_required(fields.get("docs_required")),
            additional_conditions=_coerce_string_list(fields.get("additional_conditions")),
            period_for_presentation_days=period_days,
            amount_tolerance_percent=_coerce_decimal(fields.get("tolerance")),
            partial_shipments=_str_or_none(shipment.get("partial_shipments")),
            transshipment=_str_or_none(shipment.get("transshipment")),
            drafts=drafts,
            confirmation_instructions=_str_or_none(fields.get("confirmation_instructions")),
            instructions_to_paying_bank=_str_or_none(
                fields.get("instructions_to_paying_accepting_negotiating_bank")
            ),
            charges=_str_or_none(
                fields.get("charges")[0] if isinstance(fields.get("charges"), list) and fields.get("charges")
                else fields.get("charges")
            ),
            advising_bank=_build_party(fields.get("advising_bank")),
            source_format="swift_mt700",
            source_message_type="MT700",
            extraction_method="swift_mt700_full",
            raw_field_dict={"fields": dict(fields), "raw": dict(raw_blocks)},
        )

    @classmethod
    def from_vision_llm_output(
        cls,
        payload: Dict[str, Any],
        *,
        extraction_method: Optional[str] = None,
        extraction_confidence: Optional[float] = None,
    ) -> "LCDocument":
        """Build an LCDocument from the vision LLM extractor's flat dict.

        The vision LLM output already uses MT700-aligned key names (see
        `multimodal_document_extractor.DOC_TYPE_SCHEMAS["letter_of_credit"]`)
        so this is mostly a 1:1 mapping with type coercion.
        """
        if not isinstance(payload, dict):
            payload = {}

        return cls(
            sequence_of_total=_str_or_none(payload.get("sequence_of_total")),
            form_of_documentary_credit=_str_or_none(
                payload.get("form_of_documentary_credit") or payload.get("form_of_doc_credit")
            ),
            lc_number=_str_or_none(
                payload.get("lc_number") or payload.get("number") or payload.get("reference")
            ),
            issue_date=_coerce_date(payload.get("issue_date") or payload.get("date_of_issue")),
            expiry=_build_expiry(payload),
            applicable_rules=_str_or_none(
                payload.get("applicable_rules") or payload.get("ucp_reference")
            ),
            applicant=_build_party(payload.get("applicant")),
            beneficiary=_build_party(payload.get("beneficiary")),
            amount=_build_amount(payload),
            availability=_build_availability(payload),
            port_of_loading=_str_or_none(payload.get("port_of_loading")),
            port_of_discharge=_str_or_none(payload.get("port_of_discharge")),
            latest_shipment_date=_coerce_date(payload.get("latest_shipment_date")),
            goods_description=_str_or_none(payload.get("goods_description")),
            documents_required=_build_documents_required(payload.get("documents_required")),
            additional_conditions=_coerce_string_list(payload.get("additional_conditions")),
            period_for_presentation_days=_coerce_int(payload.get("period_for_presentation")),
            amount_tolerance_percent=_coerce_decimal(payload.get("amount_tolerance")),
            partial_shipments=_str_or_none(payload.get("partial_shipments")),
            transshipment=_str_or_none(payload.get("transshipment") or payload.get("transhipment")),
            drafts=_build_drafts(payload),
            confirmation_instructions=_str_or_none(payload.get("confirmation_instructions")),
            instructions_to_paying_bank=_str_or_none(payload.get("instructions_to_paying_bank")),
            charges=_str_or_none(payload.get("charges")),
            issuing_bank=_build_party(payload.get("issuing_bank")),
            advising_bank=_build_party(payload.get("advising_bank")),
            confirming_bank=_build_party(payload.get("confirming_bank")),
            source_format="vision_llm",
            source_message_type="MT700",  # vision LLM is asked for MT700 fields
            extraction_method=extraction_method,
            extraction_confidence=extraction_confidence,
            raw_field_dict=dict(payload),
        )

    @classmethod
    def from_legacy_dict(cls, payload: Dict[str, Any]) -> "LCDocument":
        """Build an LCDocument from any of the legacy extractor dicts.

        Walks the alias soup the older parsers produced (`number` /
        `reference` / `lc_number`, `credit_amount` / `amount`, etc.) and
        normalizes to canonical key names. Use this when you have a dict
        and you don't care which extractor produced it.
        """
        if not isinstance(payload, dict):
            payload = {}

        # Try to detect the source format from the payload itself.
        source_format: Optional[str] = None
        if payload.get("_extraction_method"):
            source_format = "ai_first_text"
        if payload.get("schema") and "tsrv" in str(payload.get("schema") or ""):
            source_format = "iso20022"
        elif payload.get("schema") and "tsmt" in str(payload.get("schema") or ""):
            source_format = "iso20022"

        return cls(
            sequence_of_total=_str_or_none(
                payload.get("sequence_of_total") or payload.get("sequence")
            ),
            form_of_documentary_credit=_str_or_none(
                payload.get("form_of_documentary_credit") or payload.get("form_of_doc_credit")
            ),
            lc_number=_str_or_none(
                payload.get("lc_number")
                or payload.get("number")
                or payload.get("reference")
                or payload.get("documentary_credit_number")
            ),
            issue_date=_coerce_date(
                payload.get("issue_date") or payload.get("date_of_issue")
            ),
            expiry=_build_expiry(payload),
            applicable_rules=_str_or_none(
                payload.get("applicable_rules") or payload.get("ucp_reference")
            ),
            applicant=_build_party(payload.get("applicant") or payload.get("applicant_name")),
            beneficiary=_build_party(payload.get("beneficiary") or payload.get("beneficiary_name")),
            amount=_build_amount(payload),
            availability=_build_availability(payload),
            port_of_loading=_str_or_none(
                _flat(payload.get("ports"), "loading")
                or payload.get("port_of_loading")
                # swift_mt700_full nests these under shipment_details
                or _flat(payload.get("shipment_details"), "port_of_loading_airport_of_departure")
            ),
            port_of_discharge=_str_or_none(
                _flat(payload.get("ports"), "discharge")
                or payload.get("port_of_discharge")
                or _flat(payload.get("shipment_details"), "port_of_discharge_airport_of_destination")
            ),
            latest_shipment_date=_coerce_date(
                _flat(payload.get("dates"), "latest_shipment")
                or payload.get("latest_shipment_date")
                or payload.get("latest_shipment")
                # swift_mt700_full path nests under shipment_details
                or _flat(payload.get("shipment_details"), "latest_date_of_shipment")
            ),
            goods_description=_str_or_none(
                payload.get("goods_description") or payload.get("description_of_goods")
            ),
            documents_required=_build_documents_required(
                payload.get("documents_required") or payload.get("docs_required")
            ),
            additional_conditions=_coerce_string_list(
                payload.get("additional_conditions") or payload.get("conditions")
            ),
            period_for_presentation_days=_coerce_int(
                payload.get("period_for_presentation_days")
                or payload.get("period_for_presentation")
            ),
            amount_tolerance_percent=_coerce_decimal(
                payload.get("amount_tolerance_percent") or payload.get("tolerance") or payload.get("amount_tolerance")
            ),
            partial_shipments=_str_or_none(payload.get("partial_shipments")),
            transshipment=_str_or_none(payload.get("transshipment") or payload.get("transhipment")),
            drafts=_build_drafts(payload),
            confirmation_instructions=_str_or_none(payload.get("confirmation_instructions")),
            instructions_to_paying_bank=_str_or_none(
                payload.get("instructions_to_paying_bank")
                or payload.get("instructions_to_paying_accepting_negotiating_bank")
            ),
            charges=_str_or_none(payload.get("charges")),
            issuing_bank=_build_party(payload.get("issuing_bank")),
            advising_bank=_build_party(payload.get("advising_bank")),
            confirming_bank=_build_party(payload.get("confirming_bank")),
            source_format=source_format or "legacy_dict",
            extraction_method=payload.get("_extraction_method"),
            extraction_confidence=_coerce_float(payload.get("_extraction_confidence")),
            raw_field_dict=dict(payload),
        )

    # =======================================================================
    # Serializers — produce shapes downstream consumers expect
    # =======================================================================

    def to_lc_context(self) -> Dict[str, Any]:
        """Render this LCDocument as the legacy `lc_context` dict shape.

        Downstream consumers (validation, presentation, required-fields
        derivation) read from a flat dict with the keys below. We populate
        BOTH the canonical key (e.g. `lc_number`) AND any historical aliases
        any consumer might still grep for, so this is non-breaking when
        swapped in for a raw extractor output.
        """
        ctx: Dict[str, Any] = {}

        # MT700 mandatory — flat keys
        if self.sequence_of_total is not None:
            ctx["sequence_of_total"] = self.sequence_of_total
        if self.form_of_documentary_credit is not None:
            ctx["form_of_documentary_credit"] = self.form_of_documentary_credit
            ctx["form_of_doc_credit"] = self.form_of_documentary_credit  # alias
        if self.lc_number is not None:
            ctx["lc_number"] = self.lc_number
            ctx["number"] = self.lc_number  # alias for legacy consumers
            ctx["reference"] = self.lc_number  # alias
        if self.issue_date is not None:
            ctx["issue_date"] = self.issue_date.isoformat()
            ctx["date_of_issue"] = self.issue_date.isoformat()  # alias
        if self.expiry is not None:
            if self.expiry.date is not None:
                ctx["expiry_date"] = self.expiry.date.isoformat()
            if self.expiry.place is not None:
                ctx["expiry_place"] = self.expiry.place
        if self.applicable_rules is not None:
            ctx["applicable_rules"] = self.applicable_rules
            ctx["ucp_reference"] = self.applicable_rules  # alias
        if self.applicant is not None:
            ctx["applicant"] = self.applicant.to_string()
            ctx["applicant_party"] = self.applicant.model_dump(exclude_none=True)
        if self.beneficiary is not None:
            ctx["beneficiary"] = self.beneficiary.to_string()
            ctx["beneficiary_party"] = self.beneficiary.model_dump(exclude_none=True)
        if self.amount is not None:
            if self.amount.value is not None:
                ctx["amount"] = float(self.amount.value)
            if self.amount.currency is not None:
                ctx["currency"] = self.amount.currency
        if self.availability is not None:
            if self.availability.available_with is not None:
                ctx["available_with"] = self.availability.available_with
            if self.availability.available_by is not None:
                ctx["available_by"] = self.availability.available_by
        if self.port_of_loading is not None:
            ctx["port_of_loading"] = self.port_of_loading
        if self.port_of_discharge is not None:
            ctx["port_of_discharge"] = self.port_of_discharge
        if self.latest_shipment_date is not None:
            ctx["latest_shipment_date"] = self.latest_shipment_date.isoformat()
            ctx["latest_shipment"] = self.latest_shipment_date.isoformat()  # alias
        if self.goods_description is not None:
            ctx["goods_description"] = self.goods_description
        if self.documents_required:
            ctx["documents_required"] = [doc.raw_text for doc in self.documents_required]
            ctx["documents_required_detailed"] = [
                doc.model_dump(exclude_none=True) for doc in self.documents_required
            ]
        if self.additional_conditions:
            ctx["additional_conditions"] = list(self.additional_conditions)
        if self.period_for_presentation_days is not None:
            ctx["period_for_presentation"] = self.period_for_presentation_days

        # MT700 important-optional
        if self.amount_tolerance_percent is not None:
            ctx["amount_tolerance"] = float(self.amount_tolerance_percent)
        if self.partial_shipments is not None:
            ctx["partial_shipments"] = self.partial_shipments
        if self.transshipment is not None:
            ctx["transshipment"] = self.transshipment
        if self.drafts is not None:
            if self.drafts.drafts_at is not None:
                ctx["drafts_at"] = self.drafts.drafts_at
            if self.drafts.drawee is not None:
                ctx["drawee"] = self.drafts.drawee
        if self.confirmation_instructions is not None:
            ctx["confirmation_instructions"] = self.confirmation_instructions
        if self.instructions_to_paying_bank is not None:
            ctx["instructions_to_paying_bank"] = self.instructions_to_paying_bank
        if self.charges is not None:
            ctx["charges"] = self.charges

        # Auxiliary parties
        if self.issuing_bank is not None:
            ctx["issuing_bank"] = self.issuing_bank.to_string()
        if self.advising_bank is not None:
            ctx["advising_bank"] = self.advising_bank.to_string()
        if self.confirming_bank is not None:
            ctx["confirming_bank"] = self.confirming_bank.to_string()

        # Lineage tags
        if self.source_format is not None:
            ctx["_source_format"] = self.source_format
        if self.source_message_type is not None:
            ctx["_source_message_type"] = self.source_message_type
        if self.extraction_method is not None:
            ctx["_extraction_method"] = self.extraction_method
        if self.extraction_confidence is not None:
            ctx["_extraction_confidence"] = self.extraction_confidence

        return ctx


# ---------------------------------------------------------------------------
# Coercion helpers — kept private (module-level) so the model body stays
# focused on shape, not parsing.
# ---------------------------------------------------------------------------


def _unwrap_single(value: Any) -> Any:
    """Unwrap a one-element list/tuple into its scalar.

    swift_mt700_full wraps repeatable MT700 tags (44E, 44F, 44C, 46A, 47A,
    etc.) as lists even when the LC only provides one instance. Every coercer
    in this module calls this helper first so callers never have to know.
    """
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]
    return value


def _str_or_none(value: Any) -> Optional[str]:
    value = _unwrap_single(value)
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s or None
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    return None


def _coerce_int(value: Any) -> Optional[int]:
    value = _unwrap_single(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Tolerate "21 DAYS" / "30 days from B/L date" — pull the leading int.
        m = "".join(ch for ch in s if ch.isdigit())
        if m:
            try:
                return int(m[:6])  # cap at 6 digits to avoid junk
            except ValueError:
                return None
    return None


def _normalize_number_string(raw: str) -> str:
    """Normalize a number string that might be in US or European format.

    Critical: a naive ``.replace(",", "")`` converts European ``36450,00``
    (thirty-six thousand four hundred fifty) into ``3645000`` (three million
    six hundred forty-five thousand) — a 100x error on LC amounts that
    silently poisons every downstream tolerance/limit check.

    Heuristic:
    - If the string contains both ``.`` and ``,``, whichever character comes
      LAST is the decimal separator.
    - If only ``,``, treat the last comma as decimal iff exactly 1-2 digits
      follow it (European).  Otherwise treat all commas as thousands.
    - If only ``.``, treat the last dot as decimal iff 1-2 digits follow
      it.  Otherwise (European "1.500.000") treat all dots as thousands.
    - Otherwise return as-is.
    """
    if not raw:
        return raw
    s = raw.strip().replace("%", "")
    if not s:
        return s
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        if s.rfind(",") > s.rfind("."):
            return s.replace(".", "").replace(",", ".")
        return s.replace(",", "")
    if has_comma:
        last_comma = s.rfind(",")
        after = s[last_comma + 1:]
        if after.isdigit() and 1 <= len(after) <= 2:
            before = s[:last_comma].replace(",", "")
            return f"{before}.{after}"
        return s.replace(",", "")
    if has_dot:
        last_dot = s.rfind(".")
        after = s[last_dot + 1:]
        if after.isdigit() and 1 <= len(after) <= 2:
            before = s[:last_dot].replace(".", "")
            return f"{before}.{after}"
        return s.replace(".", "")
    return s


def _coerce_float(value: Any) -> Optional[float]:
    value = _unwrap_single(value)
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(_normalize_number_string(value))
        except ValueError:
            return None
    return None


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    value = _unwrap_single(value)
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str):
        s = _normalize_number_string(value)
        if not s:
            return None
        try:
            return Decimal(s)
        except InvalidOperation:
            return None
    return None


def _coerce_date(value: Any) -> Optional[date_type]:
    value = _unwrap_single(value)
    if value is None:
        return None
    if isinstance(value, date_type) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Try ISO formats first.
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        # MT700 31D often comes as "YYMMDD" or "YYMMDD<place>".
        digits = "".join(ch for ch in s[:6] if ch.isdigit())
        if len(digits) == 6:
            try:
                yy = int(digits[:2])
                mm = int(digits[2:4])
                dd = int(digits[4:6])
                year = 2000 + yy if yy < 80 else 1900 + yy
                return date_type(year, mm, dd)
            except ValueError:
                return None
    return None


def _coerce_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            if isinstance(item, str):
                if item.strip():
                    out.append(item.strip())
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("raw_text")
                    or item.get("display_name")
                    or item.get("description")
                    or ""
                )
                if isinstance(text, str) and text.strip():
                    out.append(text.strip())
        return out
    return []


def _flat(container: Any, key: str) -> Any:
    """Safely read a key from a possibly-nested dict."""
    if isinstance(container, dict):
        return container.get(key)
    return None


def _build_party(value: Any) -> Optional[LCParty]:
    """Accept a string, dict, or None and return an LCParty (or None)."""
    if value is None:
        return None
    if isinstance(value, LCParty):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # If it looks multiline, treat first line as name and the rest as
        # the address blob.
        lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
        if len(lines) >= 2:
            return LCParty(name=lines[0], address=LCAddress(raw="\n".join(lines[1:])))
        return LCParty(name=s)
    if isinstance(value, dict):
        name = (
            value.get("name")
            or value.get("Nm")
            or value.get("party_name")
            or None
        )
        address_value = (
            value.get("address")
            or value.get("PstlAdr")
            or value.get("postal_address")
        )
        address: Optional[LCAddress] = None
        if isinstance(address_value, str):
            address = LCAddress(raw=address_value.strip()) if address_value.strip() else None
        elif isinstance(address_value, dict):
            address = LCAddress(
                raw=address_value.get("raw"),
                street=address_value.get("street") or address_value.get("StrtNm"),
                city=address_value.get("city") or address_value.get("TwnNm"),
                region=address_value.get("region") or address_value.get("CtrySubDvsn"),
                postal_code=address_value.get("postal_code") or address_value.get("PstCd"),
                country=address_value.get("country"),
                country_code=address_value.get("country_code") or address_value.get("Ctry"),
            )
        return LCParty(
            name=_str_or_none(name),
            address=address,
            bic=_str_or_none(value.get("bic") or value.get("BICFI")),
            country_code=_str_or_none(value.get("country") or value.get("country_code")),
        )
    return None


def _build_amount(payload: Dict[str, Any]) -> Optional[LCAmount]:
    """Pull an LCAmount out of any of the legacy shapes (scalar / nested)."""
    raw_amount = payload.get("amount")
    raw_currency = payload.get("currency") or payload.get("currency_code") or payload.get("ccy")

    # If amount is already a dict, prefer its inner shape.
    if isinstance(raw_amount, dict):
        value = _coerce_decimal(raw_amount.get("value") or raw_amount.get("amount"))
        currency = _str_or_none(raw_amount.get("currency") or raw_currency)
        if value is None and currency is None:
            return None
        return LCAmount(value=value, currency=currency)

    # `credit_amount` is the swift_mt700_full key.
    credit_amount = payload.get("credit_amount")
    if isinstance(credit_amount, dict):
        value = _coerce_decimal(credit_amount.get("amount") or credit_amount.get("value"))
        currency = _str_or_none(credit_amount.get("currency") or raw_currency)
        if value is None and currency is None:
            return None
        return LCAmount(value=value, currency=currency)

    value = _coerce_decimal(raw_amount)
    currency = _str_or_none(raw_currency)
    if value is None and currency is None:
        return None
    return LCAmount(value=value, currency=currency)


def _build_expiry(payload: Dict[str, Any]) -> Optional[LCExpiry]:
    """MT700 Field 31D — date and place. Sources differ in shape."""
    # Vision LLM: top-level expiry_date + expiry_place
    flat_date = _coerce_date(payload.get("expiry_date") or payload.get("date_of_expiry"))
    flat_place = _str_or_none(payload.get("expiry_place"))

    # ISO 20022 path nests under `dates`
    dates_obj = payload.get("dates")
    if isinstance(dates_obj, dict):
        flat_date = flat_date or _coerce_date(dates_obj.get("expiry"))
        flat_place = flat_place or _str_or_none(dates_obj.get("place_of_expiry"))

    # swift_mt700_full nests under `expiry_details`
    expiry_obj = payload.get("expiry_details")
    if isinstance(expiry_obj, dict):
        flat_date = flat_date or _coerce_date(
            expiry_obj.get("date") or expiry_obj.get("date_iso") or expiry_obj.get("iso")
        )
        flat_place = flat_place or _str_or_none(expiry_obj.get("place"))

    if flat_date is None and flat_place is None:
        return None
    return LCExpiry(date=flat_date, place=flat_place)


def _build_availability(payload: Dict[str, Any]) -> Optional[LCAvailability]:
    """MT700 Field 41a — Available With + Available By."""
    # Vision LLM produces top-level available_with / available_by
    with_value = payload.get("available_with")
    by_value = payload.get("available_by")

    # swift_mt700_full nests under `available_with`
    if isinstance(with_value, dict):
        bank = _str_or_none(with_value.get("bank") or with_value.get("name"))
        bic = _str_or_none(with_value.get("bic") or with_value.get("BICFI"))
        by = _str_or_none(with_value.get("by") or by_value)
        if bank is None and bic is None and by is None:
            return None
        return LCAvailability(available_with=bank, available_with_bic=bic, available_by=by)

    bank = _str_or_none(with_value)
    by = _str_or_none(by_value)
    if bank is None and by is None:
        return None
    return LCAvailability(available_with=bank, available_by=by)


def _build_drafts(payload: Dict[str, Any]) -> Optional[LCDrafts]:
    drafts_at = _str_or_none(payload.get("drafts_at"))
    drawee = _str_or_none(payload.get("drawee"))
    # swift_mt700_full nests under `shipment`
    shipment_obj = payload.get("shipment")
    if isinstance(shipment_obj, dict):
        drafts_at = drafts_at or _str_or_none(shipment_obj.get("drafts_at"))
        drawee = drawee or _str_or_none(shipment_obj.get("drawee"))

    if drafts_at is None and drawee is None:
        return None
    return LCDrafts(drafts_at=drafts_at, drawee=drawee)


def _build_documents_required(value: Any) -> List[LCDocumentRequirement]:
    """Build a list of LCDocumentRequirement from any of the input shapes."""
    out: List[LCDocumentRequirement] = []
    if value is None:
        return out
    if isinstance(value, str):
        if value.strip():
            out.append(LCDocumentRequirement(raw_text=value.strip()))
        return out
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(LCDocumentRequirement(raw_text=item.strip()))
            elif isinstance(item, dict):
                raw = (
                    item.get("raw_text")
                    or item.get("text")
                    or item.get("display_name")
                    or item.get("description")
                    or ""
                )
                if isinstance(raw, str) and raw.strip():
                    out.append(
                        LCDocumentRequirement(
                            raw_text=raw.strip(),
                            document_type=_str_or_none(
                                item.get("document_type") or item.get("doc_type") or item.get("type")
                            ),
                            field_requirements=_coerce_string_list(
                                item.get("field_requirements") or item.get("required_fields")
                            ),
                        )
                    )
    return out


__all__ = [
    "LCAddress",
    "LCAmount",
    "LCAvailability",
    "LCDocument",
    "LCDocumentRequirement",
    "LCDrafts",
    "LCExpiry",
    "LCParty",
]
