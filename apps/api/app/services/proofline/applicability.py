"""Deterministic Proofline module applicability by payment arrangement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.models import PaymentArrangement


@dataclass(frozen=True)
class ModuleApplicability:
    module: str
    category: str
    applicable: bool
    required: bool
    reason: str
    state: str


PAYMENT_MODULES = (
    "lcopilot",
    "open_account_review",
    "advance_payment_review",
    "staged_payment_review",
    "documentary_collection_review",
    "supply_chain_finance_review",
    "receivables_finance_review",
    "consignment_review",
    "payment_terms_review",
)

PAYMENT_ROUTING: dict[PaymentArrangement, tuple[str, str]] = {
    PaymentArrangement.LETTER_OF_CREDIT: (
        "lcopilot",
        "A letter of credit is present, so the existing LCopilot review is required.",
    ),
    PaymentArrangement.OPEN_ACCOUNT: (
        "open_account_review",
        "Open-account readiness depends on the order, contract, shipment evidence, invoice approval, and payment terms.",
    ),
    PaymentArrangement.ADVANCE_TT: (
        "advance_payment_review",
        "Advance-payment evidence and allocation to the order and invoice must be checked.",
    ),
    PaymentArrangement.PARTIAL_ADVANCE_BALANCE: (
        "staged_payment_review",
        "The advance, remaining balance, and release trigger must be reconciled.",
    ),
    PaymentArrangement.DOCUMENTS_AGAINST_PAYMENT: (
        "documentary_collection_review",
        "Collection instructions and payment-before-release conditions must be checked.",
    ),
    PaymentArrangement.DOCUMENTS_AGAINST_ACCEPTANCE: (
        "documentary_collection_review",
        "Collection instructions, acceptance tenor, and maturity evidence must be checked.",
    ),
    PaymentArrangement.BUYER_LED_SUPPLY_CHAIN_FINANCE: (
        "supply_chain_finance_review",
        "Buyer approval, eligible invoice, platform terms, assignment, and funding status must be checked.",
    ),
    PaymentArrangement.FACTORING_RECEIVABLES_FINANCE: (
        "receivables_finance_review",
        "Receivable eligibility, assignment, risk coverage, and recourse terms must be checked.",
    ),
    PaymentArrangement.CONSIGNMENT: (
        "consignment_review",
        "Title, inventory reporting, sales trigger, remittance, and return rights must be checked.",
    ),
    PaymentArrangement.OTHER: (
        "payment_terms_review",
        "The payment structure requires an analyst-defined evidence and payment scope.",
    ),
}


def _resolve_arrangement(value: PaymentArrangement | str) -> PaymentArrangement:
    try:
        return value if isinstance(value, PaymentArrangement) else PaymentArrangement(value)
    except ValueError as exc:
        raise ValueError(f"Unknown Proofline payment arrangement: {value!r}") from exc


def applicability_for(
    payment_arrangement: PaymentArrangement | str,
    *,
    context: Mapping[str, Any],
) -> list[ModuleApplicability]:
    arrangement = _resolve_arrangement(payment_arrangement)
    selected_module, selected_reason = PAYMENT_ROUTING[arrangement]
    results: list[ModuleApplicability] = []

    for module in PAYMENT_MODULES:
        selected = module == selected_module
        results.append(
            ModuleApplicability(
                module=module,
                category="payment",
                applicable=selected,
                required=selected,
                reason=(
                    selected_reason
                    if selected
                    else f"{module.replace('_', ' ').title()} does not apply to {arrangement.value.replace('_', ' ')}."
                ),
                state="pending" if selected else "not_applicable",
            )
        )

    for module, reason in (
        ("document_review", "Every trade case requires document and cross-document review."),
        ("sanctions", "Every submitted trade case requires applicable party screening."),
        ("rulhub", "Applicable requirements must be resolved for the submitted transaction context."),
    ):
        results.append(
            ModuleApplicability(
                module=module,
                category="core",
                applicable=True,
                required=True,
                reason=reason,
                state="pending",
            )
        )

    contextual = (
        ("cbam", "cbam_requested", "CBAM evaluation was requested or identified as applicable."),
        ("eudr", "eudr_requested", "EUDR evaluation was requested or identified as applicable."),
        ("ein", "ein_requested", "Identity or credential verification through EIN was requested."),
        (
            "buyer_requirements",
            "buyer_requirements_present",
            "Buyer-specific requirements are attached to this case.",
        ),
    )
    for module, flag, applicable_reason in contextual:
        selected = bool(context.get(flag, False))
        results.append(
            ModuleApplicability(
                module=module,
                category="regulatory" if module in {"cbam", "eudr"} else "evidence",
                applicable=selected,
                required=selected,
                reason=(
                    applicable_reason
                    if selected
                    else f"{module.upper() if module in {'cbam', 'eudr', 'ein'} else 'Buyer requirements'} was not applicable or requested for this case."
                ),
                state="pending" if selected else "not_applicable",
            )
        )
    return results


__all__ = ["ModuleApplicability", "PAYMENT_ROUTING", "applicability_for"]

