"""
Date Logic Handler
Validates logical date relationships in LC documents
Used by UCP600-31 and ISBP-A11
"""

from datetime import datetime
from typing import Dict, Any
from dateutil.parser import parse

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate date logic across LC document

    Checks:
    1. Issue date < Latest shipment date < Expiry date
    2. All dates are valid and parseable
    3. No illogical date sequences
    """

    try:
        # Extract dates
        issue_date = lc_document.get('issue_date')
        shipment_date = lc_document.get('latest_shipment_date')
        expiry_date = lc_document.get('expiry_date')

        # Track parsed dates
        parsed_dates = {}
        date_fields = {
            'issue_date': issue_date,
            'latest_shipment_date': shipment_date,
            'expiry_date': expiry_date
        }

        # Parse all available dates
        for field, date_value in date_fields.items():
            if date_value:
                try:
                    parsed_dates[field] = parse(str(date_value))
                except Exception as e:
                    return {
                        "status": "fail",
                        "details": f"Invalid date format in {field}: {date_value}",
                        "field_location": field,
                        "suggested_fix": "Use standard date format (YYYY-MM-DD)"
                    }

        # Check required dates
        if 'latest_shipment_date' in parsed_dates and 'expiry_date' in parsed_dates:
            shipment_dt = parsed_dates['latest_shipment_date']
            expiry_dt = parsed_dates['expiry_date']

            if shipment_dt >= expiry_dt:
                return {
                    "status": "fail",
                    "details": "Latest shipment date must be before expiry date",
                    "field_location": "latest_shipment_date,expiry_date",
                    "suggested_fix": "Ensure shipment date precedes expiry date"
                }

        # Check issue date logic if available
        if 'issue_date' in parsed_dates:
            issue_dt = parsed_dates['issue_date']

            if 'expiry_date' in parsed_dates:
                expiry_dt = parsed_dates['expiry_date']
                if issue_dt >= expiry_dt:
                    return {
                        "status": "fail",
                        "details": "Issue date must be before expiry date",
                        "field_location": "issue_date,expiry_date",
                        "suggested_fix": "Ensure issue date precedes expiry date"
                    }

            if 'latest_shipment_date' in parsed_dates:
                shipment_dt = parsed_dates['latest_shipment_date']
                if issue_dt > shipment_dt:
                    return {
                        "status": "warning",
                        "details": "Issue date is after shipment date (unusual but may be valid)",
                        "field_location": "issue_date,latest_shipment_date",
                        "suggested_fix": "Verify date sequence is correct"
                    }

        # Check date ranges for reasonableness
        current_date = datetime.now()
        for field, date_dt in parsed_dates.items():
            # Check for dates too far in the past
            if (current_date - date_dt).days > 365:
                return {
                    "status": "warning",
                    "details": f"{field} is more than 1 year in the past",
                    "field_location": field,
                    "suggested_fix": "Verify date is correct"
                }

            # Check for dates too far in the future
            if (date_dt - current_date).days > 365:
                return {
                    "status": "warning",
                    "details": f"{field} is more than 1 year in the future",
                    "field_location": field,
                    "suggested_fix": "Verify date is correct"
                }

        return {
            "status": "pass",
            "details": "Date logic validation passed",
            "field_location": ",".join(parsed_dates.keys())
        }

    except Exception as e:
        return {
            "status": "error",
            "details": f"Error validating date logic: {str(e)}",
            "field_location": "date_fields"
        }