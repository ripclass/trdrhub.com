"""
BD-008: Certificate of Origin Handler
Validates certificate of origin issuer requirements for Bangladesh
"""

from typing import Dict, Any

def validate(lc_document: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate certificate of origin issuer for Bangladesh exports

    Recognized issuers:
    - DCCI (Dhaka Chamber of Commerce & Industry)
    - CCCI (Chittagong Chamber of Commerce & Industry)
    - BGMEA (Bangladesh Garment Manufacturers & Exporters Association)
    - EPB (Export Promotion Board)
    """

    try:
        # Check if certificate of origin is required
        required_docs = lc_document.get('required_documents', [])

        origin_cert_required = any(
            'origin' in str(doc).lower() and 'certificate' in str(doc).lower()
            for doc in required_docs
        )

        if not origin_cert_required:
            return {
                "status": "pass",
                "details": "Certificate of origin not required",
                "field_location": "required_documents"
            }

        # Check certificate requirements specification
        cert_requirements = lc_document.get('certificate_requirements', '').lower()

        # Recognized Bangladesh issuing authorities
        recognized_issuers = {
            'dcci': 'Dhaka Chamber of Commerce & Industry',
            'ccci': 'Chittagong Chamber of Commerce & Industry',
            'bgmea': 'Bangladesh Garment Manufacturers & Exporters Association',
            'epb': 'Export Promotion Board',
            'chamber': 'Chamber of Commerce',
            'export promotion board': 'Export Promotion Board',
            'garment': 'BGMEA or similar garment association'
        }

        # Check if any recognized issuer is specified
        specified_issuer = None
        for issuer_key, issuer_name in recognized_issuers.items():
            if issuer_key in cert_requirements:
                specified_issuer = issuer_name
                break

        if specified_issuer:
            return {
                "status": "pass",
                "details": f"Certificate of origin from recognized issuer: {specified_issuer}",
                "field_location": "certificate_requirements"
            }

        # Check for general certificate requirements
        if 'signed' in cert_requirements or 'dated' in cert_requirements:
            return {
                "status": "warning",
                "details": "Certificate signing requirements specified but issuer not identified",
                "field_location": "certificate_requirements",
                "suggested_fix": "Specify issuer: DCCI, CCCI, BGMEA, or Export Promotion Board"
            }

        # Check beneficiary country to determine likely issuer
        beneficiary_country = lc_document.get('beneficiary', {}).get('country', '').lower()

        if 'bangladesh' in beneficiary_country or 'bd' in beneficiary_country:
            return {
                "status": "warning",
                "details": "Bangladesh beneficiary should specify certificate issuer",
                "field_location": "certificate_requirements",
                "suggested_fix": "Add issuer specification: 'Certificate of Origin issued by DCCI/CCCI/BGMEA'"
            }

        # No specific issuer requirements found
        return {
            "status": "pass",
            "details": "Certificate of origin requirements present but issuer not critical",
            "field_location": "certificate_requirements"
        }

    except Exception as e:
        return {
            "status": "error",
            "details": f"Error validating origin certificate: {str(e)}",
            "field_location": "certificate_requirements"
        }