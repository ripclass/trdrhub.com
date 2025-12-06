"""
Sanctions Screening Integration for LCopilot

Automatically extracts parties from LC documents and screens them against
sanctions lists during validation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.services.sanctions_screening import (
    get_screening_service,
    ScreeningInput,
    ComprehensiveScreeningResult,
    ScreeningMatch,
)

logger = logging.getLogger(__name__)

# Party types to extract and screen
PARTY_FIELDS = [
    ("applicant", "applicant_name", "Applicant"),
    ("beneficiary", "beneficiary_name", "Beneficiary"),
    ("issuing_bank", "issuing_bank", "Issuing Bank"),
    ("advising_bank", "advising_bank", "Advising Bank"),
    ("confirming_bank", "confirming_bank", "Confirming Bank"),
    ("notify_party", "notify_party", "Notify Party"),
    ("consignee", "consignee", "Consignee"),
    ("shipper", "shipper", "Shipper"),
]


def extract_parties_from_lc(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all parties from LC documents and related documents.
    
    Returns list of party dicts with name, type, country, and source.
    """
    parties = []
    lc_context = payload.get("lc") or {}
    mt700 = lc_context.get("mt700") or {}
    invoice = payload.get("invoice") or {}
    bl = payload.get("bill_of_lading") or {}
    
    # 1. Extract from LC
    for field_key, alt_key, party_type in PARTY_FIELDS:
        name = (
            lc_context.get(field_key) or 
            lc_context.get(alt_key) or 
            lc_context.get(f"{field_key}_name") or
            mt700.get(field_key) or
            mt700.get(alt_key)
        )
        
        if name and isinstance(name, str) and len(name.strip()) > 2:
            # Extract country if available
            country = (
                lc_context.get(f"{field_key}_country") or
                lc_context.get(f"country_{field_key}")
            )
            
            parties.append({
                "name": name.strip(),
                "type": party_type,
                "country": country,
                "source": "Letter of Credit",
            })
    
    # 2. Extract from MT700 specific fields
    mt700_party_fields = {
        "50": ("Applicant", "applicant"),
        "59": ("Beneficiary", "beneficiary"),
        "41A": ("Available With", "available_with_bank"),
        "42A": ("Drawee", "drawee"),
        "44A": ("Place of Taking Charge", None),
        "51D": ("Applicant Bank", "applicant_bank"),
        "52A": ("Issuing Bank", "issuing_bank"),
        "53A": ("Reimbursing Bank", "reimbursing_bank"),
        "78": ("Instructions to Paying Bank", None),
    }
    
    for field_code, (party_type, field_name) in mt700_party_fields.items():
        value = mt700.get(field_code) or mt700.get(field_name)
        if value and isinstance(value, str) and len(value.strip()) > 2:
            # Skip if we already have this party
            if not any(p["name"].lower() == value.strip().lower() for p in parties):
                parties.append({
                    "name": value.strip(),
                    "type": party_type,
                    "country": None,
                    "source": "LC (MT700)",
                })
    
    # 3. Extract from Commercial Invoice
    invoice_parties = [
        ("seller", "Seller"),
        ("buyer", "Buyer"),
        ("consignee", "Consignee"),
        ("notify_party", "Notify Party"),
        ("shipper", "Shipper"),
    ]
    
    for field, party_type in invoice_parties:
        name = invoice.get(field) or invoice.get(f"{field}_name")
        if name and isinstance(name, str) and len(name.strip()) > 2:
            if not any(p["name"].lower() == name.strip().lower() for p in parties):
                parties.append({
                    "name": name.strip(),
                    "type": party_type,
                    "country": invoice.get(f"{field}_country"),
                    "source": "Commercial Invoice",
                })
    
    # 4. Extract from Bill of Lading
    bl_parties = [
        ("shipper", "Shipper"),
        ("consignee", "Consignee"),
        ("notify_party", "Notify Party"),
        ("carrier", "Carrier"),
        ("vessel_owner", "Vessel Owner"),
    ]
    
    for field, party_type in bl_parties:
        name = bl.get(field) or bl.get(f"{field}_name")
        if name and isinstance(name, str) and len(name.strip()) > 2:
            if not any(p["name"].lower() == name.strip().lower() for p in parties):
                parties.append({
                    "name": name.strip(),
                    "type": party_type,
                    "country": bl.get(f"{field}_country"),
                    "source": "Bill of Lading",
                })
    
    # 5. Extract vessel from B/L (for vessel screening)
    vessel_name = bl.get("vessel_name") or bl.get("vessel")
    if vessel_name and isinstance(vessel_name, str) and len(vessel_name.strip()) > 2:
        parties.append({
            "name": vessel_name.strip(),
            "type": "Vessel",
            "country": bl.get("flag_state") or bl.get("flag"),
            "source": "Bill of Lading",
            "is_vessel": True,
            "imo": bl.get("imo_number") or bl.get("imo"),
            "mmsi": bl.get("mmsi"),
        })
    
    # Deduplicate by name (case-insensitive)
    seen_names = set()
    unique_parties = []
    for party in parties:
        name_lower = party["name"].lower()
        if name_lower not in seen_names:
            seen_names.add(name_lower)
            unique_parties.append(party)
    
    logger.info(f"Extracted {len(unique_parties)} unique parties from LC documents")
    return unique_parties


async def screen_lc_parties(
    payload: Dict[str, Any],
    lists: Optional[List[str]] = None
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Screen all extracted parties against sanctions lists.
    
    Args:
        payload: The validation payload containing LC and document data
        lists: Optional list of specific sanctions lists to screen against
        
    Returns:
        Tuple of (list of sanctions issues, has_match flag)
    """
    parties = extract_parties_from_lc(payload)
    
    if not parties:
        logger.info("No parties found in LC documents to screen")
        return [], False
    
    service = get_screening_service()
    issues = []
    has_match = False
    
    for party in parties:
        try:
            # Determine screening type
            screening_type = "vessel" if party.get("is_vessel") else "party"
            
            # Build screening input
            additional_data = {}
            if party.get("is_vessel"):
                additional_data = {
                    "imo": party.get("imo"),
                    "mmsi": party.get("mmsi"),
                    "flag_state": party.get("country"),
                }
            
            input_data = ScreeningInput(
                query=party["name"],
                screening_type=screening_type,
                country=party.get("country"),
                lists=lists or [],
                additional_data=additional_data,
            )
            
            # Run screening
            result = await service.screen(input_data)
            
            # Check result
            if result.status in ("match", "potential_match"):
                if result.status == "match":
                    has_match = True
                
                # Build issue for display
                severity = "critical" if result.status == "match" else "major"
                match_info = result.matches[0] if result.matches else None
                
                issue = _build_sanctions_issue(
                    party=party,
                    result=result,
                    match_info=match_info,
                    severity=severity,
                )
                issues.append(issue)
                
                logger.warning(
                    f"Sanctions {result.status} found for {party['type']}: {party['name']} "
                    f"(score={result.highest_score:.2f}, lists={result.lists_screened})"
                )
        
        except Exception as e:
            logger.error(f"Error screening party {party['name']}: {e}")
            continue
    
    logger.info(
        f"Screened {len(parties)} parties: {len(issues)} sanctions issues found, "
        f"has_match={has_match}"
    )
    
    return issues, has_match


def _build_sanctions_issue(
    party: Dict[str, Any],
    result: ComprehensiveScreeningResult,
    match_info: Optional[ScreeningMatch],
    severity: str,
) -> Dict[str, Any]:
    """
    Build a sanctions issue in the same format as other validation issues.
    """
    party_type = party["type"]
    party_name = party["name"]
    source = party["source"]
    
    # Determine rule code based on match type
    is_vessel = party.get("is_vessel", False)
    rule_code = "SANCTIONS-VESSEL-1" if is_vessel else "SANCTIONS-PARTY-1"
    
    # Build title
    if result.status == "match":
        title = f"Sanctioned {party_type} Detected"
    else:
        title = f"Potential Sanctions Match: {party_type}"
    
    # Build expected vs actual
    if match_info:
        matched_name = match_info.matched_name
        match_score = f"{match_info.match_score:.0%}"
        matched_list = match_info.list_name
        programs = ", ".join(match_info.programs) if match_info.programs else "N/A"
    else:
        matched_name = "Unknown"
        match_score = f"{result.highest_score:.0%}"
        matched_list = ", ".join(result.lists_screened)
        programs = "N/A"
    
    # Build message
    if result.status == "match":
        message = (
            f"The {party_type.lower()} '{party_name}' from {source} matches a sanctioned entity "
            f"on {matched_list}. LC processing should be halted until compliance review is complete."
        )
    else:
        message = (
            f"The {party_type.lower()} '{party_name}' from {source} has a potential match "
            f"({match_score}) with an entity on {matched_list}. Manual review recommended."
        )
    
    return {
        "rule": rule_code,
        "title": title,
        "passed": False,
        "severity": severity,
        "message": message,
        "expected": f"No sanctions matches for {party_type.lower()}",
        "actual": f"{'Match' if result.status == 'match' else 'Potential match'}: {matched_name} ({match_score} confidence)",
        "documents": [source],
        "document_names": [source],
        "document_ids": [],
        "display_card": True,
        "ruleset_domain": "icc.lcopilot.sanctions",
        "not_applicable": False,
        "suggestion": result.recommendation,
        
        # Sanctions-specific fields
        "sanctions_details": {
            "party_name": party_name,
            "party_type": party_type,
            "matched_name": matched_name,
            "match_score": result.highest_score,
            "match_status": result.status,
            "risk_level": result.risk_level,
            "lists_screened": result.lists_screened,
            "programs": programs,
            "flags": result.flags,
            "certificate_id": result.certificate_id,
        },
    }


async def run_sanctions_screening_for_validation(
    payload: Dict[str, Any],
    existing_issues: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
    """
    Run sanctions screening as part of LCopilot validation.
    
    Returns:
        Tuple of (updated_issues, should_block, sanctions_summary)
    """
    sanctions_issues, has_match = await screen_lc_parties(payload)
    
    # Add sanctions issues to existing issues
    updated_issues = existing_issues + sanctions_issues
    
    # Build sanctions summary
    parties = extract_parties_from_lc(payload)
    
    sanctions_summary = {
        "screened": True,
        "parties_screened": len(parties),
        "matches": len([i for i in sanctions_issues if i.get("severity") == "critical"]),
        "potential_matches": len([i for i in sanctions_issues if i.get("severity") == "major"]),
        "clear": len(parties) - len(sanctions_issues),
        "should_block": has_match,
        "screened_at": datetime.utcnow().isoformat() + "Z",
        "issues": [
            {
                "party": i.get("sanctions_details", {}).get("party_name"),
                "type": i.get("sanctions_details", {}).get("party_type"),
                "status": i.get("sanctions_details", {}).get("match_status"),
                "score": i.get("sanctions_details", {}).get("match_score"),
            }
            for i in sanctions_issues
        ],
    }
    
    return updated_issues, has_match, sanctions_summary

