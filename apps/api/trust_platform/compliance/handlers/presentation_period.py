"""
UCP600-14: Presentation Period Handler
Validates documents are presented within 21 days of shipment date
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from dateutil.parser import parse

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate presentation period compliance

    UCP600 Article 14(c): Documents must be presented within 21 days after shipment date
    """

    try:
        # Get shipment date
        shipment_date = lc_document.get('latest_shipment_date')
        if not shipment_date:
            return {
                "status": "fail",
                "details": "Latest shipment date not specified",
                "field_location": "latest_shipment_date",
                "suggested_fix": "Add latest shipment date to credit"
            }

        # Check if presentation period is specified
        presentation_period = lc_document.get('presentation_period', '')

        if not presentation_period:
            return {
                "status": "fail",
                "details": "Presentation period not specified",
                "field_location": "presentation_period",
                "suggested_fix": "Specify presentation period (recommended: 21 days after shipment)"
            }

        # Parse presentation period
        period_str = str(presentation_period).lower()

        if '21' in period_str and 'day' in period_str:
            return {
                "status": "pass",
                "details": "Standard 21-day presentation period specified",
                "field_location": "presentation_period"
            }

        # Extract days from text
        import re
        days_match = re.search(r'(\d+)\s*day', period_str)

        if days_match:
            days = int(days_match.group(1))
            if days <= 21:
                return {
                    "status": "pass",
                    "details": f"{days}-day presentation period complies with UCP600",
                    "field_location": "presentation_period"
                }
            else:
                return {
                    "status": "warning",
                    "details": f"{days}-day period exceeds UCP600 recommended 21 days",
                    "field_location": "presentation_period",
                    "suggested_fix": "Consider reducing to 21 days or less"
                }
        else:
            return {
                "status": "fail",
                "details": "Presentation period format unclear or not specified",
                "field_location": "presentation_period",
                "suggested_fix": "Specify clear presentation period (e.g., '21 days after shipment')"
            }

    except Exception as e:
        return {
            "status": "error",
            "details": f"Error validating presentation period: {str(e)}",
            "field_location": "presentation_period"
        }