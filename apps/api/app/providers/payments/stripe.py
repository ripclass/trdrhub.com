"""
Stripe payment provider implementation for international payments.

Stripe is used for USD payments and international customers,
providing robust payment processing with excellent API.
"""

import stripe
import hmac
import hashlib
import json
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .base import (
    PaymentProvider, PaymentIntent, PaymentResult, RefundResult,
    WebhookEvent, PaymentStatus, PaymentMethod, PaymentProviderError,
    PaymentProviderFactory
)


class StripeProvider(PaymentProvider):
    """Stripe payment provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Stripe provider.

        Required config:
        - api_key: Stripe secret API key
        - publishable_key: Stripe publishable key (for frontend)
        - webhook_secret: Stripe webhook endpoint secret
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.publishable_key = config.get("publishable_key")
        self.webhook_secret = config.get("webhook_secret")

        # Set Stripe API key
        stripe.api_key = self.api_key

        self.validate_config()

    def _get_provider_name(self) -> str:
        return "stripe"

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str = "USD",
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        payment_method_types: Optional[List[str]] = None
    ) -> PaymentIntent:
        """Create Stripe payment intent."""

        try:
            # Convert amount to cents (Stripe's smallest unit)
            amount_cents = self.format_amount(amount, currency)

            # Prepare metadata for Stripe (flatten nested objects)
            stripe_metadata = {}
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        stripe_metadata[key] = json.dumps(value)
                    else:
                        stripe_metadata[key] = str(value)

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                customer=customer_id,
                description=description or "LCopilot LC Validation Service",
                metadata=stripe_metadata,
                payment_method_types=payment_method_types or ['card'],
                setup_future_usage='off_session' if customer_id else None,  # Save for future payments
            )

            return PaymentIntent(
                id=intent.id,
                amount=amount,
                currency=currency,
                status=self._map_stripe_status(intent.status),
                payment_method_types=intent.payment_method_types,
                client_secret=intent.client_secret,
                metadata={
                    'stripe_intent_id': intent.id,
                    'original_metadata': metadata
                },
                created_at=datetime.utcfromtimestamp(intent.created)
            )

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error creating payment intent: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error creating Stripe payment intent: {str(e)}")

    def get_payment_status(self, payment_id: str) -> PaymentResult:
        """Get payment status from Stripe."""

        try:
            intent = stripe.PaymentIntent.retrieve(payment_id)

            success = intent.status == 'succeeded'
            status = self._map_stripe_status(intent.status)

            # Get payment method details if available
            payment_method = None
            if intent.charges and intent.charges.data:
                charge = intent.charges.data[0]
                if charge.payment_method_details:
                    payment_method = self._map_stripe_payment_method(charge.payment_method_details)

            return PaymentResult(
                success=success,
                payment_id=payment_id,
                transaction_id=intent.charges.data[0].id if intent.charges.data else None,
                status=status,
                amount=self.parse_amount(intent.amount, intent.currency),
                currency=intent.currency.upper(),
                payment_method=payment_method,
                raw_response=intent.to_dict()
            )

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error getting payment status: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error getting Stripe payment status: {str(e)}")

    def capture_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> PaymentResult:
        """Capture a Stripe payment intent."""

        try:
            capture_params = {}
            if amount is not None:
                capture_params['amount_to_capture'] = self.format_amount(amount, 'USD')

            intent = stripe.PaymentIntent.capture(payment_id, **capture_params)

            success = intent.status == 'succeeded'
            status = self._map_stripe_status(intent.status)

            return PaymentResult(
                success=success,
                payment_id=payment_id,
                transaction_id=intent.charges.data[0].id if intent.charges.data else None,
                status=status,
                amount=self.parse_amount(intent.amount, intent.currency),
                currency=intent.currency.upper(),
                raw_response=intent.to_dict()
            )

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error capturing payment: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error capturing Stripe payment: {str(e)}")

    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Refund a Stripe payment."""

        try:
            # Get the payment intent to find the charge
            intent = stripe.PaymentIntent.retrieve(payment_id)
            if not intent.charges.data:
                raise PaymentProviderError("No charges found for this payment")

            charge_id = intent.charges.data[0].id

            # Create refund parameters
            refund_params = {'charge': charge_id}
            if amount is not None:
                refund_params['amount'] = self.format_amount(amount, intent.currency)
            if reason:
                refund_params['reason'] = reason

            refund = stripe.Refund.create(**refund_params)

            success = refund.status == 'succeeded'

            return RefundResult(
                success=success,
                refund_id=refund.id,
                original_payment_id=payment_id,
                amount=self.parse_amount(refund.amount, refund.currency),
                status=PaymentStatus.SUCCESS if success else PaymentStatus.FAILED,
                metadata={'stripe_refund': refund.to_dict()}
            )

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error processing refund: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error processing Stripe refund: {str(e)}")

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """Verify Stripe webhook signature."""

        try:
            stripe.Webhook.construct_event(
                payload, signature, webhook_secret or self.webhook_secret
            )
            return True
        except (stripe.error.SignatureVerificationError, ValueError):
            return False

    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse Stripe webhook event."""

        event_type = payload.get('type', '')
        event_data = payload.get('data', {}).get('object', {})

        # Extract payment information
        payment_id = None
        transaction_id = None
        amount = None
        currency = None
        status = None

        if event_type.startswith('payment_intent.'):
            payment_id = event_data.get('id')
            amount = self.parse_amount(event_data.get('amount', 0), event_data.get('currency', 'usd'))
            currency = event_data.get('currency', '').upper()
            status = self._map_stripe_status(event_data.get('status'))

            # Get transaction ID from charges if available
            charges = event_data.get('charges', {}).get('data', [])
            if charges:
                transaction_id = charges[0].get('id')

        elif event_type.startswith('charge.'):
            transaction_id = event_data.get('id')
            payment_id = event_data.get('payment_intent')
            amount = self.parse_amount(event_data.get('amount', 0), event_data.get('currency', 'usd'))
            currency = event_data.get('currency', '').upper()

            # Map charge status
            if event_data.get('status') == 'succeeded':
                status = PaymentStatus.SUCCESS
            elif event_data.get('status') == 'failed':
                status = PaymentStatus.FAILED
            else:
                status = PaymentStatus.PENDING

        return WebhookEvent(
            event_id=payload.get('id', f"stripe_{int(datetime.utcnow().timestamp())}"),
            event_type=event_type,
            payment_id=payment_id,
            transaction_id=transaction_id,
            status=status,
            amount=amount,
            currency=currency,
            timestamp=datetime.utcfromtimestamp(payload.get('created', 0)),
            raw_data=payload,
            is_verified=True
        )

    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a Stripe customer."""

        try:
            customer_data = {'email': email}
            if name:
                customer_data['name'] = name
            if phone:
                customer_data['phone'] = phone
            if metadata:
                # Flatten metadata for Stripe
                stripe_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        stripe_metadata[key] = json.dumps(value)
                    else:
                        stripe_metadata[key] = str(value)
                customer_data['metadata'] = stripe_metadata

            customer = stripe.Customer.create(**customer_data)
            return customer.id

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error creating customer: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error creating Stripe customer: {str(e)}")

    def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a Stripe customer."""

        try:
            update_data = {}
            if email:
                update_data['email'] = email
            if name:
                update_data['name'] = name
            if phone:
                update_data['phone'] = phone
            if metadata:
                # Flatten metadata for Stripe
                stripe_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        stripe_metadata[key] = json.dumps(value)
                    else:
                        stripe_metadata[key] = str(value)
                update_data['metadata'] = stripe_metadata

            if update_data:
                stripe.Customer.modify(customer_id, **update_data)

            return True

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error updating customer: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error updating Stripe customer: {str(e)}")

    def get_supported_currencies(self) -> List[str]:
        """Currencies supported by Stripe."""
        return ["USD", "EUR", "GBP", "CAD", "AUD", "SGD", "BDT"]

    def get_supported_payment_methods(self) -> List[PaymentMethod]:
        """Payment methods supported by Stripe."""
        return [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.DIGITAL_WALLET
        ]

    def validate_config(self) -> bool:
        """Validate Stripe configuration."""
        required_keys = ["api_key", "publishable_key"]
        for key in required_keys:
            if not self.config.get(key):
                raise PaymentProviderError(f"Missing required Stripe config: {key}")
        return True

    def _map_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """Map Stripe status to our standard status."""
        status_mapping = {
            'requires_payment_method': PaymentStatus.PENDING,
            'requires_confirmation': PaymentStatus.PENDING,
            'requires_action': PaymentStatus.PENDING,
            'processing': PaymentStatus.PROCESSING,
            'succeeded': PaymentStatus.SUCCESS,
            'requires_capture': PaymentStatus.PROCESSING,
            'canceled': PaymentStatus.CANCELLED,
        }
        return status_mapping.get(stripe_status, PaymentStatus.PENDING)

    def _map_stripe_payment_method(self, payment_method_details) -> str:
        """Map Stripe payment method to our standard method."""
        if hasattr(payment_method_details, 'card'):
            return PaymentMethod.CREDIT_CARD
        elif hasattr(payment_method_details, 'bank_transfer'):
            return PaymentMethod.BANK_TRANSFER
        elif hasattr(payment_method_details, 'us_bank_account'):
            return PaymentMethod.BANK_TRANSFER
        else:
            return PaymentMethod.CREDIT_CARD

    def test_connection(self) -> bool:
        """Test connection to Stripe API."""
        try:
            # Try to retrieve account information
            stripe.Account.retrieve()
            return True
        except Exception:
            return False

    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str = "USD",
        success_url: str = "",
        cancel_url: str = "",
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for hosted payment page.

        This is an alternative to PaymentIntents for simpler integration.
        """
        try:
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price_data': {
                        'currency': currency.lower(),
                        'product_data': {
                            'name': description or 'LCopilot LC Validation Service',
                        },
                        'unit_amount': self.format_amount(amount, currency),
                    },
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
            }

            if customer_id:
                session_data['customer'] = customer_id

            if metadata:
                # Flatten metadata for Stripe
                stripe_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        stripe_metadata[key] = json.dumps(value)
                    else:
                        stripe_metadata[key] = str(value)
                session_data['metadata'] = stripe_metadata

            session = stripe.checkout.Session.create(**session_data)

            return {
                'checkout_session_id': session.id,
                'checkout_url': session.url,
                'payment_intent_id': session.payment_intent
            }

        except stripe.error.StripeError as e:
            raise PaymentProviderError(
                f"Stripe error creating checkout session: {str(e)}",
                error_code=e.code,
                provider_error=e.json_body if hasattr(e, 'json_body') else None
            )
        except Exception as e:
            raise PaymentProviderError(f"Error creating Stripe checkout session: {str(e)}")


# Register the provider
PaymentProviderFactory.register_provider("stripe", StripeProvider)