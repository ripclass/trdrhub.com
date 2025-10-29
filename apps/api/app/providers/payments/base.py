"""
Base payment provider interface for LCopilot billing system.

This module defines the abstract interface that all payment providers must implement,
enabling support for multiple payment gateways (Stripe, SSLCommerz, etc.).
"""

import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    MOBILE_BANKING = "mobile_banking"
    DIGITAL_WALLET = "digital_wallet"


@dataclass
class PaymentIntent:
    """Represents a payment intent/session."""
    id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_method_types: List[str]
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class PaymentResult:
    """Result of a payment operation."""
    success: bool
    payment_id: str
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    payment_method: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class RefundResult:
    """Result of a refund operation."""
    success: bool
    refund_id: str
    original_payment_id: str
    amount: Decimal
    status: PaymentStatus
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WebhookEvent:
    """Webhook event from payment provider."""
    event_id: str
    event_type: str
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    status: Optional[PaymentStatus] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
    is_verified: bool = False


class PaymentProvider(ABC):
    """Abstract base class for payment providers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize payment provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider_name = self._get_provider_name()

    @abstractmethod
    def _get_provider_name(self) -> str:
        """Return the name of the payment provider."""
        pass

    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        payment_method_types: Optional[List[str]] = None
    ) -> PaymentIntent:
        """
        Create a new payment intent/session.

        Args:
            amount: Payment amount
            currency: Currency code (BDT, USD, etc.)
            customer_id: Customer identifier
            description: Payment description
            metadata: Additional metadata
            return_url: Success return URL
            cancel_url: Cancellation return URL
            payment_method_types: Allowed payment methods

        Returns:
            PaymentIntent object

        Raises:
            PaymentProviderError: If payment intent creation fails
        """
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> PaymentResult:
        """
        Get current status of a payment.

        Args:
            payment_id: Payment identifier

        Returns:
            PaymentResult with current status

        Raises:
            PaymentProviderError: If status retrieval fails
        """
        pass

    @abstractmethod
    def capture_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> PaymentResult:
        """
        Capture a previously authorized payment.

        Args:
            payment_id: Payment identifier
            amount: Amount to capture (None for full amount)

        Returns:
            PaymentResult with capture result

        Raises:
            PaymentProviderError: If capture fails
        """
        pass

    @abstractmethod
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> RefundResult:
        """
        Refund a completed payment.

        Args:
            payment_id: Original payment identifier
            amount: Amount to refund (None for full refund)
            reason: Reason for refund

        Returns:
            RefundResult with refund details

        Raises:
            PaymentProviderError: If refund fails
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Verify webhook signature for security.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature
            webhook_secret: Webhook secret key

        Returns:
            True if signature is valid

        Raises:
            PaymentProviderError: If verification fails
        """
        pass

    @abstractmethod
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """
        Parse webhook payload into standardized event.

        Args:
            payload: Raw webhook payload

        Returns:
            WebhookEvent object

        Raises:
            PaymentProviderError: If parsing fails
        """
        pass

    @abstractmethod
    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a customer in the payment provider system.

        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone
            metadata: Additional customer data

        Returns:
            Customer ID in provider system

        Raises:
            PaymentProviderError: If customer creation fails
        """
        pass

    @abstractmethod
    def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update customer information.

        Args:
            customer_id: Customer identifier
            email: Updated email
            name: Updated name
            phone: Updated phone
            metadata: Updated metadata

        Returns:
            True if update successful

        Raises:
            PaymentProviderError: If update fails
        """
        pass

    def get_supported_currencies(self) -> List[str]:
        """
        Get list of supported currencies.

        Returns:
            List of currency codes
        """
        return self.config.get("supported_currencies", ["BDT", "USD"])

    def get_supported_payment_methods(self) -> List[PaymentMethod]:
        """
        Get list of supported payment methods.

        Returns:
            List of PaymentMethod enums
        """
        return [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.BANK_TRANSFER
        ]

    def format_amount(self, amount: Decimal, currency: str) -> int:
        """
        Format amount for provider API (usually in cents/smallest unit).

        Args:
            amount: Decimal amount
            currency: Currency code

        Returns:
            Amount in smallest currency unit
        """
        if currency.upper() == "BDT":
            # BDT is in paisa (1 BDT = 100 paisa)
            return int(amount * 100)
        elif currency.upper() == "USD":
            # USD is in cents
            return int(amount * 100)
        else:
            # Default to 2 decimal places
            return int(amount * 100)

    def parse_amount(self, amount_cents: int, currency: str) -> Decimal:
        """
        Parse amount from provider format back to decimal.

        Args:
            amount_cents: Amount in smallest currency unit
            currency: Currency code

        Returns:
            Decimal amount
        """
        return Decimal(str(amount_cents)) / Decimal("100")

    def validate_config(self) -> bool:
        """
        Validate provider configuration.

        Returns:
            True if configuration is valid

        Raises:
            PaymentProviderError: If configuration is invalid
        """
        required_keys = ["api_key", "webhook_secret"]
        for key in required_keys:
            if key not in self.config:
                raise PaymentProviderError(f"Missing required config key: {key}")
        return True


class PaymentProviderError(Exception):
    """Base exception for payment provider errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        provider_error: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.provider_error = provider_error


class PaymentProviderFactory:
    """Factory for creating payment provider instances."""

    _providers = {}

    @classmethod
    def register_provider(cls, name: str, provider_class):
        """Register a payment provider class."""
        cls._providers[name] = provider_class

    @classmethod
    def create_provider(cls, name: str, config: Dict[str, Any]) -> PaymentProvider:
        """Create a payment provider instance."""
        if name not in cls._providers:
            raise ValueError(f"Unknown payment provider: {name}")

        provider_class = cls._providers[name]
        return provider_class(config)

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())