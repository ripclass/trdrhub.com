"""
Sandbox mock connectors for development and testing.
Provides realistic mock responses for all integration types.
"""

import uuid
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class SandboxBankConnector:
    """Mock bank connector for development testing."""

    def __init__(self):
        self.mock_delay = 2.0  # Simulate API latency

    async def submit_lc_validation(self, swift_message: Dict[str, Any]) -> Dict[str, Any]:
        """Mock LC validation submission."""
        await asyncio.sleep(self.mock_delay)

        # Simulate different validation outcomes
        outcomes = ['approved', 'rejected', 'pending_review', 'requires_amendment']
        outcome = random.choice(outcomes)

        response = {
            'reference_id': str(uuid.uuid4()),
            'lc_number': swift_message.get('lc_number', 'LC123456789'),
            'validation_status': outcome,
            'processing_time_ms': int(self.mock_delay * 1000),
            'timestamp': datetime.utcnow().isoformat(),
            'details': {
                'swift_format_valid': True,
                'bic_codes_valid': True,
                'amount_verification': 'passed',
                'expiry_date_check': 'valid',
                'document_requirements': 'compliant'
            }
        }

        if outcome == 'rejected':
            response['rejection_reasons'] = [
                'Invalid beneficiary BIC code',
                'LC amount exceeds credit limit'
            ]
        elif outcome == 'requires_amendment':
            response['amendment_requirements'] = [
                'Update expiry date to minimum 30 days',
                'Clarify shipping terms in field 44C'
            ]

        return response

    async def query_lc_status(self, lc_number: str) -> Dict[str, Any]:
        """Mock LC status query."""
        await asyncio.sleep(0.5)

        statuses = ['issued', 'advised', 'confirmed', 'utilized', 'expired']
        status_value = random.choice(statuses)

        return {
            'lc_number': lc_number,
            'status': status_value,
            'issue_date': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'expiry_date': (datetime.utcnow() + timedelta(days=60)).isoformat(),
            'available_amount': float(Decimal(str(random.uniform(10000, 500000))).quantize(Decimal('0.01'))),
            'currency': 'USD',
            'issuing_bank': 'Mock International Bank',
            'advising_bank': 'Mock Regional Bank',
            'last_updated': datetime.utcnow().isoformat()
        }


class SandboxCustomsConnector:
    """Mock customs authority connector for development testing."""

    def __init__(self):
        self.mock_delay = 3.0  # Customs APIs are typically slower

    async def submit_declaration(self, declaration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock customs declaration submission."""
        await asyncio.sleep(self.mock_delay)

        # Simulate different declaration outcomes
        outcomes = ['accepted', 'rejected', 'examination_required', 'pending_documents']
        outcome = random.choice(outcomes)

        declaration_number = f"CUS{random.randint(100000, 999999)}"

        response = {
            'declaration_number': declaration_number,
            'status': outcome,
            'submission_timestamp': datetime.utcnow().isoformat(),
            'estimated_clearance_time': (datetime.utcnow() + timedelta(hours=random.randint(4, 48))).isoformat(),
            'customs_office': declaration_data.get('customs_office', 'MOCK_CUSTOMS_01'),
            'processing_fee': float(Decimal(str(random.uniform(50, 500))).quantize(Decimal('0.01'))),
            'currency': 'USD'
        }

        if outcome == 'accepted':
            response['clearance_code'] = f"CLR{random.randint(10000, 99999)}"
            response['duties_calculated'] = {
                'import_duty': float(Decimal(str(random.uniform(100, 5000))).quantize(Decimal('0.01'))),
                'vat': float(Decimal(str(random.uniform(200, 3000))).quantize(Decimal('0.01'))),
                'total_amount': float(Decimal(str(random.uniform(400, 8000))).quantize(Decimal('0.01'))),
                'currency': 'USD'
            }
        elif outcome == 'examination_required':
            response['examination_details'] = {
                'type': 'physical_inspection',
                'scheduled_date': (datetime.utcnow() + timedelta(days=2)).isoformat(),
                'location': 'Warehouse A, Dock 12',
                'required_documents': ['commercial_invoice', 'packing_list', 'certificate_of_origin']
            }
        elif outcome == 'rejected':
            response['rejection_reasons'] = [
                'Missing certificate of origin',
                'HS code classification requires verification'
            ]

        return response

    async def query_declaration_status(self, declaration_number: str) -> Dict[str, Any]:
        """Mock declaration status query."""
        await asyncio.sleep(0.8)

        statuses = ['submitted', 'under_review', 'cleared', 'examination_required', 'released']
        status_value = random.choice(statuses)

        return {
            'declaration_number': declaration_number,
            'status': status_value,
            'submission_date': (datetime.utcnow() - timedelta(days=2)).isoformat(),
            'last_updated': datetime.utcnow().isoformat(),
            'customs_office': 'MOCK_CUSTOMS_01',
            'clearance_date': datetime.utcnow().isoformat() if status_value == 'cleared' else None,
            'tracking_reference': f"TRK{random.randint(100000, 999999)}"
        }

    async def get_hs_classification(self, product_description: str, country_code: str) -> Dict[str, Any]:
        """Mock HS code classification."""
        await asyncio.sleep(1.0)

        # Mock HS codes for common products
        mock_classifications = [
            {
                'hs_code': '8517.12.00',
                'description': 'Telephones for cellular networks or for other wireless networks',
                'confidence_score': 0.95
            },
            {
                'hs_code': '6203.42.40',
                'description': 'Mens or boys trousers, bib and brace overalls, cotton',
                'confidence_score': 0.88
            },
            {
                'hs_code': '8471.30.01',
                'description': 'Portable automatic data processing machines',
                'confidence_score': 0.92
            }
        ]

        classification = random.choice(mock_classifications)

        return {
            'product_description': product_description,
            'country_code': country_code,
            'classifications': [classification],
            'recommended_hs_code': classification['hs_code'],
            'classification_confidence': classification['confidence_score'],
            'additional_requirements': [
                'Certificate of conformity may be required',
                'Import license verification recommended'
            ]
        }


class SandboxLogisticsConnector:
    """Mock logistics provider connector for development testing."""

    def __init__(self):
        self.mock_delay = 1.5

    async def get_shipping_quote(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock shipping quote."""
        await asyncio.sleep(self.mock_delay)

        # Generate realistic shipping options
        services = [
            {
                'service_name': 'Express International',
                'service_code': 'EXP_INTL',
                'transit_time': '2-3 business days',
                'cost': float(Decimal(str(random.uniform(150, 300))).quantize(Decimal('0.01'))),
                'currency': 'USD',
                'includes_insurance': True,
                'tracking_included': True
            },
            {
                'service_name': 'Standard International',
                'service_code': 'STD_INTL',
                'transit_time': '5-7 business days',
                'cost': float(Decimal(str(random.uniform(80, 150))).quantize(Decimal('0.01'))),
                'currency': 'USD',
                'includes_insurance': False,
                'tracking_included': True
            },
            {
                'service_name': 'Economy International',
                'service_code': 'ECO_INTL',
                'transit_time': '10-15 business days',
                'cost': float(Decimal(str(random.uniform(30, 80))).quantize(Decimal('0.01'))),
                'currency': 'USD',
                'includes_insurance': False,
                'tracking_included': False
            }
        ]

        quote_id = f"QUO{random.randint(100000, 999999)}"

        return {
            'quote_id': quote_id,
            'origin': shipment_data.get('origin', {}),
            'destination': shipment_data.get('destination', {}),
            'services': services,
            'quote_valid_until': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'estimated_delivery_dates': {
                service['service_code']: (datetime.utcnow() + timedelta(days=random.randint(2, 15))).isoformat()
                for service in services
            },
            'restrictions': [
                'Lithium batteries require special declaration',
                'Dangerous goods not accepted on this route'
            ],
            'carbon_footprint': {
                'co2_emissions_kg': float(Decimal(str(random.uniform(5, 50))).quantize(Decimal('0.01'))),
                'calculation_method': 'EN 16258 standard'
            }
        }

    async def create_shipment(self, shipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock shipment creation."""
        await asyncio.sleep(self.mock_delay)

        tracking_number = f"TRK{random.randint(1000000000, 9999999999)}"

        return {
            'tracking_number': tracking_number,
            'shipment_id': str(uuid.uuid4()),
            'status': 'created',
            'pickup_date': (datetime.utcnow() + timedelta(days=1)).isoformat(),
            'estimated_delivery': (datetime.utcnow() + timedelta(days=random.randint(3, 10))).isoformat(),
            'shipping_label_url': f"https://sandbox-api.logistics.com/labels/{tracking_number}.pdf",
            'tracking_url': f"https://sandbox-tracking.logistics.com/{tracking_number}",
            'cost_breakdown': {
                'base_cost': float(Decimal(str(random.uniform(50, 200))).quantize(Decimal('0.01'))),
                'fuel_surcharge': float(Decimal(str(random.uniform(5, 25))).quantize(Decimal('0.01'))),
                'handling_fee': float(Decimal(str(random.uniform(10, 30))).quantize(Decimal('0.01'))),
                'total_cost': float(Decimal(str(random.uniform(80, 300))).quantize(Decimal('0.01'))),
                'currency': 'USD'
            }
        }

    async def track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Mock shipment tracking."""
        await asyncio.sleep(0.5)

        # Generate realistic tracking events
        statuses = ['created', 'picked_up', 'in_transit', 'customs_cleared', 'out_for_delivery', 'delivered']
        current_status = random.choice(statuses)

        events = []
        base_time = datetime.utcnow() - timedelta(days=3)

        for i, status in enumerate(statuses):
            if status == current_status:
                break
            events.append({
                'timestamp': (base_time + timedelta(hours=i*6)).isoformat(),
                'status': status,
                'location': f"Mock Location {i+1}",
                'description': f"Package {status.replace('_', ' ').title()}"
            })

        # Add current status
        events.append({
            'timestamp': datetime.utcnow().isoformat(),
            'status': current_status,
            'location': f"Mock Location {len(events)+1}",
            'description': f"Package {current_status.replace('_', ' ').title()}"
        })

        return {
            'tracking_number': tracking_number,
            'current_status': current_status,
            'estimated_delivery': (datetime.utcnow() + timedelta(days=2)).isoformat(),
            'tracking_events': events,
            'package_info': {
                'weight': '2.5 kg',
                'dimensions': '30x20x15 cm',
                'service_type': 'Express International'
            },
            'delivery_address': {
                'city': 'Mock City',
                'country': 'Mock Country',
                'postal_code': '12345'
            }
        }


class SandboxFXConnector:
    """Mock FX provider connector for development testing."""

    def __init__(self):
        self.mock_delay = 0.5

    async def get_fx_quote(self, from_currency: str, to_currency: str, amount: float) -> Dict[str, Any]:
        """Mock FX quote."""
        await asyncio.sleep(self.mock_delay)

        # Generate realistic exchange rates
        base_rates = {
            'USD': 1.0,
            'EUR': 0.85,
            'GBP': 0.73,
            'BDT': 110.0,
            'AED': 3.67,
            'SAR': 3.75,
            'INR': 83.0
        }

        from_rate = base_rates.get(from_currency, 1.0)
        to_rate = base_rates.get(to_currency, 1.0)

        # Add some realistic spread
        spread = random.uniform(0.001, 0.005)
        exchange_rate = (to_rate / from_rate) * (1 + spread)

        converted_amount = amount * exchange_rate

        quote_id = f"FX{random.randint(100000, 999999)}"

        return {
            'quote_id': quote_id,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'from_amount': amount,
            'to_amount': float(Decimal(str(converted_amount)).quantize(Decimal('0.01'))),
            'exchange_rate': float(Decimal(str(exchange_rate)).quantize(Decimal('0.0001'))),
            'spread_percentage': float(Decimal(str(spread * 100)).quantize(Decimal('0.01'))),
            'quote_valid_until': (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            'settlement_date': (datetime.utcnow() + timedelta(days=2)).isoformat(),
            'fees': {
                'transaction_fee': float(Decimal(str(amount * 0.001)).quantize(Decimal('0.01'))),
                'currency': from_currency
            },
            'market_info': {
                'mid_rate': float(Decimal(str(to_rate / from_rate)).quantize(Decimal('0.0001'))),
                'bid_rate': float(Decimal(str((to_rate / from_rate) * 0.9995)).quantize(Decimal('0.0001'))),
                'ask_rate': float(Decimal(str((to_rate / from_rate) * 1.0005)).quantize(Decimal('0.0001'))),
                'last_updated': datetime.utcnow().isoformat()
            }
        }


class SandboxConnectorRegistry:
    """Registry for all sandbox connectors."""

    def __init__(self):
        self.connectors = {
            'bank': SandboxBankConnector(),
            'customs': SandboxCustomsConnector(),
            'logistics': SandboxLogisticsConnector(),
            'fx_provider': SandboxFXConnector()
        }

    def get_connector(self, integration_type: str):
        """Get sandbox connector by type."""
        connector = self.connectors.get(integration_type)
        if not connector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sandbox connector for {integration_type} not found"
            )
        return connector

    async def health_check(self, integration_type: str) -> Dict[str, Any]:
        """Mock health check for sandbox connectors."""
        await asyncio.sleep(0.1)

        return {
            'integration_type': integration_type,
            'status': 'healthy',
            'sandbox_mode': True,
            'response_time_ms': 100,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0-sandbox'
        }

    async def simulate_webhook(self, integration_type: str, event_type: str) -> Dict[str, Any]:
        """Simulate webhook events for testing."""
        await asyncio.sleep(0.5)

        webhook_events = {
            'bank': {
                'lc_validation_complete': {
                    'event_type': 'lc_validation_complete',
                    'reference_id': str(uuid.uuid4()),
                    'lc_number': 'LC123456789',
                    'validation_result': 'approved',
                    'timestamp': datetime.utcnow().isoformat()
                }
            },
            'customs': {
                'declaration_processed': {
                    'event_type': 'declaration_processed',
                    'declaration_number': f"CUS{random.randint(100000, 999999)}",
                    'status': 'cleared',
                    'clearance_date': datetime.utcnow().isoformat()
                }
            },
            'logistics': {
                'shipment_delivered': {
                    'event_type': 'shipment_delivered',
                    'tracking_number': f"TRK{random.randint(1000000000, 9999999999)}",
                    'delivery_date': datetime.utcnow().isoformat(),
                    'delivery_location': 'Recipient Address'
                }
            }
        }

        events = webhook_events.get(integration_type, {})
        event_data = events.get(event_type)

        if not event_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook event {event_type} not supported for {integration_type}"
            )

        return event_data


# Global sandbox registry instance
sandbox_registry = SandboxConnectorRegistry()