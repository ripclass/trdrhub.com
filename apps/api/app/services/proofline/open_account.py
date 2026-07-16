"""Deterministic open-account evidence and payment-readiness checks.

This module does not decide legal compliance, payment, financing, customs, or
bank acceptance.  It identifies submitted-evidence gaps and inconsistencies
for analyst review and cites the evaluated rule reference where applicable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional


BB_FE_31_PART_D = {
    "id": "BB-FE-31-2025-PART-D",
    "version": "2025-07-31",
    "source": "Bangladesh Bank FE Circular No. 31",
    "article": "Part-D",
    "url": "https://www.bb.org.bd/mediaroom/circulars/fepd/jul312025fepd31e.pdf",
}


@dataclass(frozen=True)
class OpenAccountCheckResult:
    state: str
    findings: list[dict[str, Any]]
    expected_payment_date: Optional[date]
    rule_references: list[dict[str, Any]]


def _text(value: Any) -> str:
    if value is None or value == "":
        return "Not found in submitted evidence"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _normal_name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _money(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _rule(article: str) -> dict[str, Any]:
    return {**BB_FE_31_PART_D, "article": article}


def run_open_account_checks(context: Mapping[str, Any]) -> OpenAccountCheckResult:
    documents = context.get("documents") or {}
    payment_terms = context.get("payment_terms") or {}
    findings: list[dict[str, Any]] = []
    gap_found = False
    issue_found = False

    def add_finding(
        *,
        finding_id: str,
        category: str,
        severity: str,
        title: str,
        explanation: str,
        expected: str,
        observed: Any,
        correction: str,
        kind: str = "gap",
        rule_reference: Optional[dict[str, Any]] = None,
        evidence_references: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        nonlocal gap_found, issue_found
        if kind == "issue":
            issue_found = True
        else:
            gap_found = True
        findings.append(
            {
                "source_module": "open_account",
                "source_finding_id": finding_id,
                "category": category,
                "severity": severity,
                "title": title,
                "explanation": explanation,
                "expected": expected,
                "observed": _text(observed),
                "suggested_correction": correction,
                "automated": True,
                "visibility": "customer",
                "status": "customer_action_required",
                "rule_reference": rule_reference,
                "evidence_references": evidence_references or [],
            }
        )

    core_documents = (
        ("purchase_order", "OA-DOC-PO-1", "Purchase order"),
        ("sales_contract", "OA-DOC-CONTRACT-1", "Sales contract"),
        ("commercial_invoice", "OA-DOC-INVOICE-1", "Commercial invoice"),
        ("packing_list", "OA-DOC-PACKING-1", "Packing list"),
        ("transport_document", "OA-DOC-TRANSPORT-1", "Transport document"),
    )
    for document_type, finding_id, label in core_documents:
        if not documents.get(document_type):
            add_finding(
                finding_id=finding_id,
                category="document_presence",
                severity="high" if document_type in {"purchase_order", "sales_contract", "commercial_invoice"} else "medium",
                title=f"{label} is missing",
                explanation=f"The {label.lower()} is needed to test order, shipment, invoice, and payment readiness.",
                expected=f"A readable, current {label.lower()} linked to this trade case",
                observed="No document was submitted",
                correction=f"Upload the {label.lower()} and confirm its case reference.",
            )

    if context.get("shipment_status") == "delivered" and not documents.get("proof_of_delivery"):
        add_finding(
            finding_id="OA-DOC-POD-1",
            category="delivery_evidence",
            severity="medium",
            title="Proof of delivery is missing",
            explanation="The payment or invoice-approval trigger may depend on delivery evidence.",
            expected="Proof of delivery or buyer receipt evidence",
            observed="Shipment is marked delivered but no delivery evidence was submitted",
            correction="Upload the signed delivery, carrier, or buyer receipt evidence.",
        )

    due_days = payment_terms.get("due_days")
    trigger = payment_terms.get("trigger")
    approval_conditions = payment_terms.get("approval_conditions") or []
    if not trigger:
        add_finding(
            finding_id="OA-PAYMENT-TRIGGER-1",
            category="payment_terms",
            severity="high",
            title="Payment trigger is not evidenced",
            explanation="A due period is not actionable until the event that starts it is identified.",
            expected="A clear trigger such as invoice approval, shipment, delivery, or buyer acceptance",
            observed="No payment trigger was found",
            correction="Add or upload the agreed approval and payment-trigger terms.",
        )
    if not isinstance(due_days, int) or due_days <= 0:
        add_finding(
            finding_id="OA-PAYMENT-TENOR-1",
            category="payment_terms",
            severity="high",
            title="Payment tenor is not usable",
            explanation="The expected payment date cannot be evaluated without a positive agreed tenor.",
            expected="A positive number of days tied to the payment trigger",
            observed=due_days,
            correction="Confirm the agreed tenor and the event from which it runs.",
        )
    if trigger == "buyer_invoice_approval" and not approval_conditions:
        add_finding(
            finding_id="OA-INVOICE-APPROVAL-1",
            category="invoice_approval",
            severity="high",
            title="Buyer invoice-approval conditions are missing",
            explanation="The evidence does not show what the buyer requires before approving the invoice.",
            expected="Documented invoice-approval conditions and responsible buyer function",
            observed="Buyer approval is the trigger, but its conditions were not found",
            correction="Upload or record the buyer vendor-manual or contract approval conditions.",
        )

    if not context.get("deduction_terms_reviewed") or not context.get("chargeback_terms_reviewed"):
        add_finding(
            finding_id="OA-DEDUCTIONS-1",
            category="deductions_chargebacks",
            severity="medium",
            title="Deduction or chargeback terms are not fully evidenced",
            explanation="Unreviewed deductions, rejection rights, credit notes, or chargebacks may reduce or delay payment.",
            expected="Reviewed deduction, claim, rejection, credit-note, and chargeback clauses",
            observed="One or more clause groups were not confirmed",
            correction="Upload the governing buyer terms and mark the relevant deduction and chargeback clauses.",
        )

    trigger_date = None
    if trigger == "buyer_invoice_approval":
        trigger_date = context.get("invoice_approval_date")
    elif trigger == "invoice_date":
        trigger_date = context.get("invoice_date")
    elif trigger == "shipment":
        trigger_date = context.get("shipment_date")
    elif trigger == "delivery":
        trigger_date = context.get("delivery_date")

    calculated_payment_date: Optional[date] = None
    if isinstance(trigger_date, date) and isinstance(due_days, int) and due_days > 0:
        calculated_payment_date = trigger_date + timedelta(days=due_days)
        submitted_date = context.get("expected_payment_date")
        if isinstance(submitted_date, date) and submitted_date != calculated_payment_date:
            add_finding(
                finding_id="OA-PAYMENT-DATE-1",
                category="payment_timing",
                severity="medium",
                title="Expected payment date does not match the agreed trigger and tenor",
                explanation="The entered payment date differs from the deterministic trigger-plus-tenor calculation.",
                expected=calculated_payment_date.isoformat(),
                observed=submitted_date.isoformat(),
                correction="Confirm the approval/trigger date and tenor, then update the expected payment date.",
                kind="issue",
            )
    elif trigger and isinstance(due_days, int) and due_days > 0:
        add_finding(
            finding_id="OA-PAYMENT-TRIGGER-DATE-1",
            category="payment_timing",
            severity="medium",
            title="Payment trigger date is missing",
            explanation="The agreed tenor is present, but the triggering event is not dated.",
            expected=f"A dated {str(trigger).replace('_', ' ')} event",
            observed="No trigger date was found",
            correction="Upload or confirm dated evidence of the payment-trigger event.",
        )

    purchase_order = context.get("purchase_order") or {}
    invoice = context.get("invoice") or {}
    po_amount = _money(purchase_order.get("amount"))
    invoice_amount = _money(invoice.get("amount"))
    if po_amount is not None and invoice_amount is not None and po_amount != invoice_amount:
        add_finding(
            finding_id="OA-AMOUNT-1",
            category="value_consistency",
            severity="high",
            title="Purchase-order and invoice amounts do not match",
            explanation="The invoice value differs from the submitted order value.",
            expected=f"Invoice amount {po_amount}",
            observed=f"Invoice amount {invoice_amount}",
            correction="Correct the invoice or provide an approved order change/quantity reconciliation.",
            kind="issue",
        )
    po_currency = purchase_order.get("currency")
    invoice_currency = invoice.get("currency")
    if po_currency and invoice_currency and str(po_currency).upper() != str(invoice_currency).upper():
        add_finding(
            finding_id="OA-CURRENCY-1",
            category="currency_consistency",
            severity="high",
            title="Purchase-order and invoice currencies do not match",
            explanation="A currency mismatch can prevent buyer approval or create a pricing dispute.",
            expected=str(po_currency).upper(),
            observed=str(invoice_currency).upper(),
            correction="Correct the invoice currency or upload the buyer-approved currency amendment.",
            kind="issue",
        )
    for key, finding_id, label in (
        ("buyer_name", "OA-BUYER-1", "buyer"),
        ("seller_name", "OA-SELLER-1", "seller"),
    ):
        expected_name = purchase_order.get(key)
        observed_name = invoice.get(key)
        if expected_name and observed_name and _normal_name(expected_name) != _normal_name(observed_name):
            add_finding(
                finding_id=finding_id,
                category="party_consistency",
                severity="high",
                title=f"{label.title()} name does not match across order and invoice",
                explanation=f"The {label} identity differs between the purchase order and commercial invoice.",
                expected=str(expected_name),
                observed=str(observed_name),
                correction=f"Correct the {label} name or provide evidence that both names identify the same legal entity.",
                kind="issue",
            )

    rule_references: list[dict[str, Any]] = []
    if str(context.get("origin_country") or "").upper() == "BD":
        rule_references.append(BB_FE_31_PART_D.copy())
        if not context.get("payment_risk_coverage"):
            add_finding(
                finding_id="OA-BD-RISK-COVERAGE-1",
                category="payment_risk_evidence",
                severity="high",
                title="Open-account payment undertaking or risk coverage is not evidenced",
                explanation="The submitted Bangladesh export evidence does not identify the undertaking or payment-risk coverage supporting the open-account structure. This is an evidence review, not a determination of regulatory acceptance.",
                expected="Identifiable payment undertaking or payment-risk coverage and provider reference",
                observed="No coverage record was submitted",
                correction="Upload the undertaking, insurance, factoring, financier, or equivalent risk-coverage evidence and confirm it with the exporter’s AD bank.",
                rule_reference=_rule("Part-D, paragraph 39"),
            )

        shipment_date = context.get("shipment_date")
        submission_date = context.get("ad_bank_submission_date")
        if isinstance(shipment_date, date) and not isinstance(submission_date, date):
            add_finding(
                finding_id="OA-BD-AD-SUBMISSION-1",
                category="regulatory_evidence",
                severity="high",
                title="AD-bank export-document submission is not evidenced",
                explanation="The case does not include dated evidence that the export documents were submitted through the exporter’s AD bank.",
                expected="Dated AD-bank submission evidence linked to the shipment",
                observed="No AD-bank submission date or receipt was found",
                correction="Upload the AD-bank submission receipt or confirm the submission date with the exporter’s bank.",
                rule_reference=_rule("Part-D, paragraph 44"),
            )
        elif isinstance(shipment_date, date) and isinstance(submission_date, date):
            elapsed = (submission_date - shipment_date).days
            if elapsed < 0 or elapsed > 14:
                add_finding(
                    finding_id="OA-BD-AD-TIMING-1",
                    category="regulatory_timing",
                    severity="high",
                    title="Recorded AD-bank document submission falls outside the referenced period",
                    explanation="The recorded submission timing does not align with the evaluated Bangladesh Bank circular reference and requires analyst/AD-bank confirmation.",
                    expected="Submission completed within 14 days from shipment",
                    observed=f"Submission recorded {elapsed} days after shipment",
                    correction="Confirm the dates and submission evidence with the exporter’s AD bank and correct the case record if needed.",
                    kind="issue",
                    rule_reference=_rule("Part-D, paragraph 44"),
                )

    if context.get("financing_requested"):
        if not context.get("financing_evidence"):
            add_finding(
                finding_id="OA-FINANCE-EVIDENCE-1",
                category="financing_evidence",
                severity="high",
                title="Receivables-finance eligibility is not evidenced",
                explanation="The case requests financing but does not include the financier, eligible receivable, approval, or coverage evidence.",
                expected="Financier terms and evidence identifying an eligible approved receivable",
                observed="No financing eligibility evidence was submitted",
                correction="Upload the finance/factoring terms, eligible invoice approval, and undertaking or coverage reference.",
            )
        if not context.get("assignment_terms_reviewed"):
            add_finding(
                finding_id="OA-ASSIGNMENT-1",
                category="assignment_terms",
                severity="medium",
                title="Receivable assignment restrictions are not reviewed",
                explanation="The submitted contract may restrict assignment or require notice/consent before financing.",
                expected="Reviewed assignment, notice, consent, and recourse terms",
                observed="Assignment terms were not confirmed",
                correction="Review and upload the governing assignment and buyer-notice provisions.",
            )

    state = "issue_found" if issue_found else "evidence_incomplete" if gap_found else "clear"
    return OpenAccountCheckResult(
        state=state,
        findings=findings,
        expected_payment_date=calculated_payment_date or context.get("expected_payment_date"),
        rule_references=rule_references,
    )


__all__ = ["BB_FE_31_PART_D", "OpenAccountCheckResult", "run_open_account_checks"]
