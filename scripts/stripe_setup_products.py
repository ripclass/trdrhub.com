"""Create the launch Products/Prices in Stripe — Phase 5 (run once per mode).

Creates the seven launch products with lookup-keyed prices:

    pack_review        $29   one-off   LC Pack Review
    pack_review_memo   $49   one-off   LC Pack Review + Bank Memo
    priority_review    $79   one-off   LC Priority Review (6h)
    cbam_report        $149  one-off   CBAM Supplier-Readiness Report
    eudr_report        $149  one-off   EUDR Readiness Report
    cbam_eudr_bundle   $249  one-off   CBAM + EUDR Readiness Bundle
    retainer_monthly   $299  monthly   Retainer — 20 checks/mo (HIDDEN: never
                                       shown in the app; offer manually via a
                                       Payment Link at a customer's 3rd repeat
                                       purchase)

Idempotent: existing prices are found by lookup_key and left alone.

NOTE: in-app Checkout builds sessions with inline price_data (amounts from
app/services/checkout.py), so the app works without this script. Running it
keeps the Stripe dashboard/reports tidy and creates the retainer price that
only exists here.

Usage (test mode, then again with the live key at cutover):
    STRIPE_SECRET_KEY=sk_test_... apps/api/venv/Scripts/python scripts/stripe_setup_products.py
"""

import os
import sys

import stripe

ONE_OFF = [
    ("pack_review", "LC Pack Review", 2900,
     "Full LC presentation set, checked and cited — delivered within 24 hours."),
    ("pack_review_memo", "LC Pack Review + Bank Memo", 4900,
     "Pack review plus a bank-ready compliance memo — delivered within 24 hours."),
    ("priority_review", "LC Priority Review (6h)", 7900,
     "Pack review + bank memo with 6-hour turnaround."),
    ("cbam_report", "CBAM Supplier-Readiness Report", 14900,
     "Cited CBAM readiness assessment — delivered within 24 hours."),
    ("eudr_report", "EUDR Readiness Report", 14900,
     "Cited EUDR readiness assessment — delivered within 24 hours."),
    ("cbam_eudr_bundle", "CBAM + EUDR Readiness Bundle", 24900,
     "Both readiness reports for one supply chain — delivered within 24 hours."),
]

RETAINER = ("retainer_monthly", "LCopilot Retainer — 20 checks/month", 29900,
            "20 LC pack checks per month + email support. Offered manually — not sold in-app.")


def ensure_price(lookup_key: str, name: str, amount_cents: int, description: str,
                 recurring: bool) -> str:
    existing = stripe.Price.list(lookup_keys=[lookup_key], limit=1)
    if existing.data:
        price = existing.data[0]
        print(f"  exists  {lookup_key}: {price.id} (${amount_cents/100:.0f})")
        return price.id

    product = stripe.Product.create(name=name, description=description,
                                    metadata={"trdr_product_id": lookup_key})
    kwargs = {
        "product": product.id,
        "currency": "usd",
        "unit_amount": amount_cents,
        "lookup_key": lookup_key,
    }
    if recurring:
        kwargs["recurring"] = {"interval": "month"}
    price = stripe.Price.create(**kwargs)
    print(f"  created {lookup_key}: {price.id} (${amount_cents/100:.0f}"
          f"{'/mo' if recurring else ''})")
    return price.id


def main() -> int:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_"):
        print("Set STRIPE_SECRET_KEY (sk_test_… or sk_live_…) first.")
        return 1
    stripe.api_key = key
    mode = "LIVE" if key.startswith("sk_live_") else "TEST"
    print(f"Creating launch products in {mode} mode…")

    for lookup_key, name, amount, desc in ONE_OFF:
        ensure_price(lookup_key, name, amount, desc, recurring=False)
    ensure_price(*RETAINER, recurring=True)

    print("\nDone. The retainer price is created but hidden — offer it manually via a "
          "Payment Link from the dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
