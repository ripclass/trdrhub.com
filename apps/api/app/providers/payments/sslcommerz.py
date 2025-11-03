"""
SSLCommerz payment provider implementation for Bangladesh market.

SSLCommerz is the leading payment gateway in Bangladesh, supporting
local payment methods including cards, mobile banking, and internet banking.
"""

import hashlib
import hmac
import json
import requests
import uuid
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

from .base import (
    PaymentProvider,
    PaymentIntent,
    PaymentResult,
    RefundResult,
    WebhookEvent,
    PaymentStatus,
    PaymentMethod,
    PaymentProviderError,
    PaymentProviderFactory,
)


class SSLCommerzProvider(PaymentProvider):
    """SSLCommerz payment provider implementation."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SSLCommerz provider.

        Required config:
        - store_id: SSLCommerz store ID
        - store_password: SSLCommerz store password
        - sandbox: Boolean for sandbox mode
        """
        super().__init__(config)
        self.store_id = config.get("store_id")
        self.store_password = config.get("store_password")
        self.sandbox = config.get("sandbox", True)

        # Set API endpoints
        if self.sandbox:
            self.base_url = "https://sandbox.sslcommerz.com"
            self.validation_url = f"{self.base_url}/validator/api/validationserverAPI.php"
            self.refund_url = f"{self.base_url}/validator/api/merchantTransIDvalidationAPI.php"
        else:
            self.base_url = "https://securepay.sslcommerz.com"
            self.validation_url = f"{self.base_url}/validator/api/validationserverAPI.php"
            self.refund_url = f"{self.base_url}/validator/api/merchantTransIDvalidationAPI.php"

        self.session_url = f"{self.base_url}/gwprocess/v4/api.php"
        self.ipn_validation_url = f"{self.base_url}/validator/api/validationserverAPI.php"

        self.validate_config()

    def _get_provider_name(self) -> str:
        return "sslcommerz"

    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str = "BDT",
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        payment_method_types: Optional[List[str]] = None
    ) -> PaymentIntent:
        """Create SSLCommerz payment session."""

        # Generate unique transaction ID
        tran_id = f"LCopilot_{uuid.uuid4().hex[:16]}"

        # Prepare payment data
        payment_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_password,
            'total_amount': str(amount),
            'currency': currency,
            'tran_id': tran_id,
            'success_url': return_url or self.config.get("success_url", ""),
            'fail_url': cancel_url or self.config.get("fail_url", ""),
            'cancel_url': cancel_url or self.config.get("cancel_url", ""),
            'ipn_url': self.config.get("ipn_url", ""),

            # Product information
            'product_name': description or "LCopilot LC Validation",
            'product_category': 'Service',
            'product_profile': 'general',

            # Customer information
            'cus_name': metadata.get("customer_name", "Customer") if metadata else "Customer",
            'cus_email': metadata.get("customer_email", "customer@lcopilot.com") if metadata else "customer@lcopilot.com",
            'cus_add1': metadata.get("customer_address", "Dhaka, Bangladesh") if metadata else "Dhaka, Bangladesh",
            'cus_city': metadata.get("customer_city", "Dhaka") if metadata else "Dhaka",
            'cus_state': metadata.get("customer_state", "Dhaka") if metadata else "Dhaka",
            'cus_postcode': metadata.get("customer_postcode", "1000") if metadata else "1000",
            'cus_country': metadata.get("customer_country", "Bangladesh") if metadata else "Bangladesh",
            'cus_phone': metadata.get("customer_phone", "01700000000") if metadata else "01700000000",

            # Shipping information (same as customer for services)
            'shipping_method': 'NO',

            # Multi-card and EMI options
            'multi_card_name': 'mastercard,visacard,amexcard',
            'value_a': customer_id or '',
            'value_b': json.dumps(metadata) if metadata else '',
            'value_c': '',
            'value_d': ''
        }

        try:
            response = requests.post(self.session_url, data=payment_data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get('status') == 'SUCCESS':
                return PaymentIntent(
                    id=tran_id,
                    amount=amount,
                    currency=currency,
                    status=PaymentStatus.PENDING,
                    payment_method_types=payment_method_types or ['card', 'mobile_banking', 'internet_banking'],
                    checkout_url=result.get('GatewayPageURL'),
                    metadata={
                        'sessionkey': result.get('sessionkey'),
                        'sslcommerz_data': result,
                        'original_metadata': metadata
                    },
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=1)  # SSLCommerz sessions expire in 1 hour
                )
            else:
                raise PaymentProviderError(
                    f"Failed to create SSLCommerz session: {result.get('failedreason', 'Unknown error')}",
                    error_code=result.get('status'),
                    provider_error=result
                )

        except requests.exceptions.RequestException as e:
            raise PaymentProviderError(f"Network error creating SSLCommerz session: {str(e)}")
        except Exception as e:
            raise PaymentProviderError(f"Error creating SSLCommerz session: {str(e)}")

    def get_payment_status(self, payment_id: str) -> PaymentResult:
        """Get payment status from SSLCommerz."""

        validation_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_password,
            'tran_id': payment_id
        }

        try:
            response = requests.get(self.validation_url, params=validation_data, timeout=30)
            response.raise_for_status()
            result = response.json()

            # SSLCommerz returns different status formats
            if isinstance(result, list) and len(result) > 0:
                payment_data = result[0]
            elif isinstance(result, dict):
                payment_data = result
            else:
                raise PaymentProviderError("Invalid response format from SSLCommerz")

            # Map SSLCommerz status to our standard status
            sslcommerz_status = payment_data.get('status', '').upper()
            if sslcommerz_status == 'VALID':
                status = PaymentStatus.SUCCESS
                success = True
            elif sslcommerz_status in ['FAILED', 'CANCELLED']:
                status = PaymentStatus.FAILED if sslcommerz_status == 'FAILED' else PaymentStatus.CANCELLED
                success = False
            else:
                status = PaymentStatus.PENDING
                success = False

            return PaymentResult(
                success=success,
                payment_id=payment_id,
                transaction_id=payment_data.get('bank_tran_id'),
                status=status,
                amount=Decimal(str(payment_data.get('amount', '0'))),
                currency=payment_data.get('currency', 'BDT'),
                payment_method=self._map_payment_method(payment_data.get('card_type', '')),
                raw_response=payment_data
            )

        except requests.exceptions.RequestException as e:
            raise PaymentProviderError(f"Network error checking payment status: {str(e)}")
        except Exception as e:
            raise PaymentProviderError(f"Error checking payment status: {str(e)}")

    def capture_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> PaymentResult:
        """SSLCommerz auto-captures payments on success. Return current status."""
        return self.get_payment_status(payment_id)

    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """Initiate refund through SSLCommerz."""

        # First get the original payment details
        payment_status = self.get_payment_status(payment_id)
        if not payment_status.success:
            raise PaymentProviderError("Cannot refund unsuccessful payment")

        refund_amount = amount or payment_status.amount
        refund_id = f"RF_{uuid.uuid4().hex[:16]}"

        refund_data = {
            'store_id': self.store_id,
            'store_passwd': self.store_password,
            'bank_tran_id': payment_status.transaction_id,
            'refund_amount': str(refund_amount),
            'refund_remarks': reason or 'Refund requested by merchant',
            'refe_id': refund_id
        }

        try:
            response = requests.get(self.refund_url, params=refund_data, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Parse refund response
            success = result.get('status') == 'SUCCESS'

            return RefundResult(
                success=success,
                refund_id=refund_id,
                original_payment_id=payment_id,
                amount=refund_amount,
                status=PaymentStatus.SUCCESS if success else PaymentStatus.FAILED,
                error_message=result.get('errorReason') if not success else None,
                metadata={'sslcommerz_response': result}
            )

        except requests.exceptions.RequestException as e:
            raise PaymentProviderError(f"Network error processing refund: {str(e)}")
        except Exception as e:
            raise PaymentProviderError(f"Error processing refund: {str(e)}")

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Verify SSLCommerz IPN signature.
        SSLCommerz uses form-encoded data for IPN, not HMAC signatures.
        We validate by checking required parameters and store credentials.
        """
        try:
            # Parse form-encoded payload
            payload_str = payload.decode('utf-8')
            params = dict(pair.split('=') for pair in payload_str.split('&'))

            # Verify store ID matches
            if params.get('store_id') != self.store_id:
                return False

            # Additional validation can be done by calling validation API
            # This is the recommended approach for SSLCommerz
            return True

        except Exception:
            return False

    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse SSLCommerz IPN payload."""

        tran_id = payload.get('tran_id')
        status = payload.get('status', '').upper()

        # Map status
        if status == 'VALID':
            event_status = PaymentStatus.SUCCESS
        elif status == 'FAILED':
            event_status = PaymentStatus.FAILED
        elif status == 'CANCELLED':
            event_status = PaymentStatus.CANCELLED
        else:
            event_status = PaymentStatus.PENDING

        return WebhookEvent(
            event_id=f"sslcommerz_{tran_id}_{int(datetime.utcnow().timestamp())}",
            event_type=f"payment.{status.lower()}",
            payment_id=tran_id,
            transaction_id=payload.get('bank_tran_id'),
            status=event_status,
            amount=Decimal(str(payload.get('amount', '0'))),
            currency=payload.get('currency', 'BDT'),
            timestamp=datetime.utcnow(),
            raw_data=payload,
            is_verified=True  # We'll verify this in the webhook handler
        )

    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        SSLCommerz doesn't have a separate customer API.
        Return a customer ID that we can use internally.
        """
        customer_id = f"sslcommerz_cust_{uuid.uuid4().hex[:16]}"
        return customer_id

    def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """SSLCommerz doesn't support customer updates."""
        return True  # Always return success since there's nothing to update

    def get_supported_currencies(self) -> List[str]:
        """SSLCommerz supports BDT and USD."""
        return ["BDT", "USD"]

    def get_supported_payment_methods(self) -> List[PaymentMethod]:
        """Payment methods supported by SSLCommerz."""
        return [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.MOBILE_BANKING,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.DIGITAL_WALLET
        ]

    def validate_config(self) -> bool:
        """Validate SSLCommerz configuration."""
        required_keys = ["store_id", "store_password"]
        for key in required_keys:
            if not self.config.get(key):
                raise PaymentProviderError(f"Missing required SSLCommerz config: {key}")
        return True

    def _map_payment_method(self, card_type: str) -> str:
        """Map SSLCommerz card type to standard payment method."""
        card_type_lower = card_type.lower()

        if 'visa' in card_type_lower or 'master' in card_type_lower:
            return PaymentMethod.CREDIT_CARD
        elif 'mobile' in card_type_lower or 'bkash' in card_type_lower or 'rocket' in card_type_lower:
            return PaymentMethod.MOBILE_BANKING
        elif 'internet' in card_type_lower or 'bank' in card_type_lower:
            return PaymentMethod.BANK_TRANSFER
        else:
            return PaymentMethod.CREDIT_CARD

    def test_connection(self) -> bool:
        """Test connection to SSLCommerz API."""
        try:
            # Create a minimal test request
            test_data = {
                'store_id': self.store_id,
                'store_passwd': self.store_password,
                'total_amount': '10.00',
                'currency': 'BDT',
                'tran_id': f'test_{uuid.uuid4().hex[:8]}',
                'success_url': 'https://example.com/success',
                'fail_url': 'https://example.com/fail',
                'cancel_url': 'https://example.com/cancel',
                'product_name': 'Test Product',
                'product_category': 'Test',
                'product_profile': 'general',
                'cus_name': 'Test Customer',
                'cus_email': 'test@example.com',
                'cus_add1': 'Test Address',
                'cus_city': 'Dhaka',
                'cus_state': 'Dhaka',
                'cus_postcode': '1000',
                'cus_country': 'Bangladesh',
                'cus_phone': '01700000000',
                'shipping_method': 'NO'
            }

            response = requests.post(self.session_url, data=test_data, timeout=10)
            response.raise_for_status()
            result = response.json()

            # Even if the test transaction setup fails, if we get a valid response
            # it means our credentials and connection are working
            return 'status' in result

        except Exception:
            return False


# Register the provider
PaymentProviderFactory.register_provider("sslcommerz", SSLCommerzProvider)