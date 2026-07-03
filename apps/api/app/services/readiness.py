"""CBAM / EUDR readiness tools — Phase 3 launch (2026-07).

Questionnaire-shaped (NO PDF parsing). Two surfaces per tool:

* **Free scope check** — 5 questions → "likely in scope / out of scope /
  borderline" with reasons + the relevant deadline. Deterministic, computed
  from the regulations' own annex lists (CBAM Annex I CN chapters; EUDR
  Annex I commodities). This is generic regulation knowledge — the paid,
  cited verdict comes from the RulHub m13 corpus, not from here.
* **Paid readiness report** ($149 / $249 bundle) — 10–14 question intake →
  answers mapped against the grounded rule corpus (RulHub `m13.cbam_regulation`
  / `m13.eudr` sources via /v1/rules/lookup + /v1/rules/search) → cited
  finding cards → the SAME concierge review queue as LCopilot → delivered PDF.

Engine findings use the structured_result.issues card shape the review queue,
operator screen, and report generator already consume (title / severity /
message / expected / found / suggested_fix / clause_cited / rule).

Content anchors (verified 2026-07-03, playbook §3.2): CBAM definitive regime
live since 1 Jan 2026; 50-tonne annual de minimis (~90% of importers exempt);
certificate sales start Feb 2027, retroactive to 2026 imports; annual
declaration due 30 Sep. EUDR postponed by Reg (EU) 2025/2650 — large
operators 30 Dec 2026, SMEs 30 Jun 2027.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regulation reference data (from the regulations' annexes — scope facts, not
# rule authoring; the cited rule content comes from RulHub m13)
# ---------------------------------------------------------------------------

# CBAM Annex I product groups → representative CN prefixes.
CBAM_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "iron_steel": {
        "label": "Iron & steel (incl. downstream articles: screws, bolts, structures)",
        "cn_prefixes": ["72", "7301", "7302", "7303", "7304", "7305", "7306", "7307",
                        "7308", "7309", "7310", "7311", "7318", "7326"],
    },
    "aluminium": {"label": "Aluminium and aluminium articles", "cn_prefixes": ["76"]},
    "cement": {"label": "Cement", "cn_prefixes": ["2523", "2507"]},
    "fertilisers": {
        "label": "Fertilisers (incl. ammonia, nitric acid, nitrates)",
        "cn_prefixes": ["3102", "3105", "2808", "2814", "28342100"],
    },
    "hydrogen": {"label": "Hydrogen", "cn_prefixes": ["280410"]},
    "electricity": {"label": "Electricity", "cn_prefixes": ["2716"]},
}

# EUDR Annex I relevant commodities → representative HS/CN prefixes.
EUDR_COMMODITIES: Dict[str, Dict[str, Any]] = {
    "cattle_leather": {
        "label": "Cattle — incl. hides, leather and leather goods",
        "cn_prefixes": ["0102", "0201", "0202", "4101", "4104", "4107"],
    },
    "cocoa": {"label": "Cocoa and cocoa products (beans, paste, butter, chocolate)", "cn_prefixes": ["18"]},
    "coffee": {"label": "Coffee", "cn_prefixes": ["0901"]},
    "oil_palm": {"label": "Oil palm (palm oil and derivatives)", "cn_prefixes": ["1511", "1513", "2306", "3823"]},
    "rubber": {"label": "Natural rubber (incl. tyres and rubber articles)", "cn_prefixes": ["4001", "4005", "4006", "4007", "4008", "4011", "4012", "4013"]},
    "soya": {"label": "Soya (beans, meal, oil)", "cn_prefixes": ["1201", "1208", "1507", "2304"]},
    "wood": {"label": "Wood and wood products (incl. furniture, paper, pulp)", "cn_prefixes": ["44", "47", "48", "9403"]},
}

CBAM_DEADLINES = (
    "CBAM's definitive regime has applied since 1 January 2026. Your EU importers "
    "must file their first annual CBAM declaration by 30 September 2027 for 2026 "
    "imports, and certificate sales open February 2027 — retroactively covering 2026. "
    "They will need verified emissions data from you well before those dates."
)

EUDR_DEADLINES = (
    "EUDR compliance dates (as postponed by Regulation (EU) 2025/2650): large "
    "operators and traders from 30 December 2026; micro and small enterprises from "
    "30 June 2027. EU buyers are collecting supplier geolocation and legality "
    "evidence now to be ready."
)

# ---------------------------------------------------------------------------
# Question sets
# ---------------------------------------------------------------------------

def _q(qid: str, label: str, qtype: str = "select", options: Optional[List[Dict[str, str]]] = None,
       help_text: str = "", required: bool = True) -> Dict[str, Any]:
    q: Dict[str, Any] = {"id": qid, "label": label, "type": qtype, "required": required}
    if options:
        q["options"] = options
    if help_text:
        q["help"] = help_text
    return q


def _opts(*pairs: Tuple[str, str]) -> List[Dict[str, str]]:
    return [{"value": v, "label": l} for v, l in pairs]


YES_NO_PLANNED = _opts(("yes", "Yes"), ("planned", "Not yet, but planned"), ("no", "No"))
YES_NO_PARTIAL = _opts(("yes", "Yes"), ("partial", "Partially"), ("no", "No"))

# ---- Free scope checks (5 questions, no signup) ----------------------------

CBAM_SCOPE_QUESTIONS: List[Dict[str, Any]] = [
    _q("product_category", "What do you make or ship?", options=(
        [{"value": k, "label": v["label"]} for k, v in CBAM_CATEGORIES.items()]
        + [{"value": "other", "label": "Something else"}])),
    _q("cn_code", "CN / HS code, if you know it", qtype="text", required=False,
       help_text="e.g. 7208 for hot-rolled steel — helps us check the exact Annex I line"),
    _q("sells_to_eu", "Do these goods go to buyers in the EU?", options=YES_NO_PLANNED),
    _q("annual_volume", "Roughly how much of these goods reach the EU per year?", options=_opts(
        ("under_50t", "Under 50 tonnes"), ("over_50t", "50 tonnes or more"), ("unsure", "Not sure"))),
    _q("role", "Which best describes you?", options=_opts(
        ("non_eu_producer", "Non-EU manufacturer / exporter"),
        ("eu_importer", "EU importer"),
        ("agent", "Agent / trading company"))),
]

EUDR_SCOPE_QUESTIONS: List[Dict[str, Any]] = [
    _q("commodity", "Which commodity do your products contain or derive from?", options=(
        [{"value": k, "label": v["label"]} for k, v in EUDR_COMMODITIES.items()]
        + [{"value": "other", "label": "None of these"}])),
    _q("sells_to_eu", "Do these products go to buyers in the EU?", options=YES_NO_PLANNED),
    _q("role", "Which best describes you?", options=_opts(
        ("non_eu_supplier", "Non-EU producer / exporter supplying EU buyers"),
        ("eu_operator", "EU operator (first placer on the EU market)"),
        ("trader", "Trader / agent"))),
    _q("buyer_size", "How big is your main EU buyer?", options=_opts(
        ("large", "Large company"), ("sme", "Small / medium enterprise"), ("unknown", "Don't know"))),
    _q("geolocation", "Can you provide plot-level geolocation for where the commodity was produced?",
       options=YES_NO_PARTIAL),
]

# ---- Paid intakes (10–14 questions) ----------------------------------------

CBAM_INTAKE_QUESTIONS: List[Dict[str, Any]] = CBAM_SCOPE_QUESTIONS + [
    _q("cn_codes_full", "List the CN codes you export to the EU (comma-separated)", qtype="text",
       required=False, help_text="All 6–8 digit codes you ship — we scope each one"),
    _q("production_route", "How are the goods produced?", qtype="text", required=False,
       help_text="e.g. electric-arc furnace from scrap, blast furnace, primary smelting — drives the emissions methodology"),
    _q("emissions_data", "Do you measure the direct (and indirect) emissions of your production?",
       options=YES_NO_PARTIAL),
    _q("monitoring_system", "Do you have a monitoring plan / MRV system for installation-level emissions?",
       options=YES_NO_PARTIAL),
    _q("carbon_price_paid", "Do you pay a carbon price in your country of production?",
       options=_opts(("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")),
       help_text="A carbon price effectively paid at origin can be deducted from CBAM liability"),
    _q("buyer_requests", "Have EU buyers already asked you for CBAM emissions data?",
       options=_opts(("yes", "Yes"), ("no", "No"))),
    _q("installations", "How many production installations make the EU-bound goods?", qtype="text",
       required=False),
    _q("data_availability", "What production data can you already report per installation?", qtype="text",
       required=False, help_text="e.g. fuel use, electricity consumption, precursor inputs"),
]

EUDR_INTAKE_QUESTIONS: List[Dict[str, Any]] = EUDR_SCOPE_QUESTIONS + [
    _q("cn_codes_full", "List the HS/CN codes you ship to the EU (comma-separated)", qtype="text",
       required=False),
    _q("origin_countries", "Where is the commodity produced (countries/regions)?", qtype="text"),
    _q("supply_chain_visibility", "Do you know the specific farms/plots your commodity comes from?",
       options=YES_NO_PARTIAL),
    _q("cutoff_evidence", "Can you show the land was not deforested after 31 December 2020?",
       options=YES_NO_PARTIAL),
    _q("legality_docs", "Do you hold legality documentation for production (land rights, permits, labour)?",
       options=YES_NO_PARTIAL),
    _q("dds_experience", "Has a buyer asked you to feed their EUDR due diligence statement (DDS)?",
       options=_opts(("yes", "Yes"), ("no", "No"))),
    _q("traceability_system", "Do you run a traceability system (segregation or mass balance)?",
       options=YES_NO_PARTIAL),
    _q("mixed_sourcing", "Do you mix commodity from multiple origins in one product?", options=_opts(
        ("yes", "Yes"), ("no", "No"), ("sometimes", "Sometimes"))),
]

QUESTION_SETS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "cbam": {"scope": CBAM_SCOPE_QUESTIONS, "intake": CBAM_INTAKE_QUESTIONS},
    "eudr": {"scope": EUDR_SCOPE_QUESTIONS, "intake": EUDR_INTAKE_QUESTIONS},
}

VALID_TOOLS = ("cbam", "eudr", "both")

# Workflow types stamped on the review-queue ValidationSession rows.
READINESS_WORKFLOWS = {
    "cbam": "cbam_readiness",
    "eudr": "eudr_readiness",
    "both": "cbam_eudr_readiness",
}


# ---------------------------------------------------------------------------
# Free scope verdicts
# ---------------------------------------------------------------------------

def _match_cn(cn_code: str, prefixes: List[str]) -> bool:
    code = (cn_code or "").replace(" ", "").replace(".", "")
    return bool(code) and any(code.startswith(p) for p in prefixes)


def _cn_in_any(cn_code: str, table: Dict[str, Dict[str, Any]]) -> Optional[str]:
    for key, info in table.items():
        if _match_cn(cn_code, info["cn_prefixes"]):
            return key
    return None


def cbam_scope_verdict(answers: Dict[str, Any]) -> Dict[str, Any]:
    """likely_in_scope / likely_out_of_scope / borderline + reasons."""
    reasons: List[str] = []
    category = str(answers.get("product_category") or "other")
    cn = str(answers.get("cn_code") or "")
    sells = str(answers.get("sells_to_eu") or "no")
    volume = str(answers.get("annual_volume") or "unsure")

    cn_hit = _cn_in_any(cn, CBAM_CATEGORIES)
    covered = category in CBAM_CATEGORIES or cn_hit is not None

    if not covered:
        return {
            "verdict": "likely_out_of_scope",
            "reasons": ["Your product category is not in CBAM Annex I (cement, iron & steel, "
                        "aluminium, fertilisers, hydrogen, electricity)."],
            "deadline_note": CBAM_DEADLINES,
        }

    label = CBAM_CATEGORIES[cn_hit or category]["label"]
    reasons.append(f"{label} is a CBAM Annex I product group.")
    if cn_hit:
        reasons.append(f"CN code {cn} matches the Annex I listing.")

    if sells == "no":
        reasons.append("You said these goods don't go to EU buyers — CBAM only applies to "
                       "imports into the EU customs territory.")
        return {"verdict": "likely_out_of_scope", "reasons": reasons, "deadline_note": CBAM_DEADLINES}

    if volume == "under_50t":
        reasons.append("Under the 50-tonne annual de minimis your EU importer is likely exempt — "
                       "but the threshold is per importer per year across all CBAM goods, so "
                       "confirm their total, not just your shipments.")
        return {"verdict": "borderline", "reasons": reasons, "deadline_note": CBAM_DEADLINES}

    if volume == "unsure":
        reasons.append("Whether the 50-tonne de minimis exempts your importer depends on their "
                       "total annual CBAM-goods volume — worth confirming.")
        verdict = "borderline"
    else:
        reasons.append("At 50+ tonnes per year the de minimis exemption does not apply.")
        verdict = "likely_in_scope"

    if sells == "planned":
        reasons.append("Scope starts when the goods are imported into the EU — prepare before "
                       "the first shipment.")

    reasons.append("Your EU importers will need installation-level embedded-emissions data from "
                   "you to file their declarations.")
    return {"verdict": verdict, "reasons": reasons, "deadline_note": CBAM_DEADLINES}


def eudr_scope_verdict(answers: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    commodity = str(answers.get("commodity") or "other")
    sells = str(answers.get("sells_to_eu") or "no")
    buyer_size = str(answers.get("buyer_size") or "unknown")
    geo = str(answers.get("geolocation") or "no")

    if commodity not in EUDR_COMMODITIES:
        return {
            "verdict": "likely_out_of_scope",
            "reasons": ["Your product doesn't appear to contain an EUDR Annex I commodity "
                        "(cattle/leather, cocoa, coffee, oil palm, rubber, soya, wood). "
                        "Check derived products carefully — the annex covers many downstream goods."],
            "deadline_note": EUDR_DEADLINES,
        }

    reasons.append(f"{EUDR_COMMODITIES[commodity]['label']} is an EUDR Annex I commodity.")

    if sells == "no":
        reasons.append("You said these products don't go to EU buyers — EUDR obligations attach "
                       "when products are placed on or exported from the EU market.")
        return {"verdict": "likely_out_of_scope", "reasons": reasons, "deadline_note": EUDR_DEADLINES}

    verdict = "likely_in_scope"
    reasons.append("Your EU buyer must file a due diligence statement — and will need geolocation, "
                   "deforestation-free evidence (post-31 Dec 2020 cutoff) and legality documentation "
                   "from you.")
    if buyer_size == "large":
        reasons.append("Large EU operators must comply from 30 December 2026.")
    elif buyer_size == "sme":
        reasons.append("SME operators comply from 30 June 2027 — but large buyers upstream may "
                       "demand your data earlier.")
    if geo in ("no", "partial"):
        reasons.append("Plot-level geolocation is the hardest requirement — start collecting it "
                       "now; without it your buyer cannot file a compliant DDS.")
    if sells == "planned":
        reasons.append("Obligations start with the first placement on the EU market — prepare first.")

    return {"verdict": verdict, "reasons": reasons, "deadline_note": EUDR_DEADLINES}


def scope_verdict(tool: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    if tool == "cbam":
        return cbam_scope_verdict(answers)
    if tool == "eudr":
        return eudr_scope_verdict(answers)
    raise ValueError(f"unknown tool: {tool}")


# ---------------------------------------------------------------------------
# One-page email summary (the email-gated lead magnet)
# ---------------------------------------------------------------------------

def build_scope_summary_html(tool: str, answers: Dict[str, Any], verdict: Dict[str, Any]) -> str:
    tool_name = "CBAM" if tool == "cbam" else "EUDR"
    verdict_label = {
        "likely_in_scope": "Likely IN scope",
        "likely_out_of_scope": "Likely OUT of scope",
        "borderline": "Borderline — needs a closer look",
    }.get(verdict["verdict"], verdict["verdict"])
    reasons_html = "".join(f"<li>{r}</li>" for r in verdict["reasons"])
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:640px;margin:0 auto;color:#1a2230">
      <h2 style="color:#0f3d3e">Your {tool_name} scope check — {verdict_label}</h2>
      <p>Here's the one-page summary of the instant check you ran on TRDR Hub.</p>
      <h3 style="color:#0f3d3e">Why</h3>
      <ul>{reasons_html}</ul>
      <h3 style="color:#0f3d3e">Deadlines that matter</h3>
      <p>{verdict["deadline_note"]}</p>
      <h3 style="color:#0f3d3e">What next</h3>
      <p>The full {tool_name} readiness report ($149) maps YOUR products, volumes and data
      readiness against the regulation clause by clause — every gap cited, with what to
      prepare and by when, reviewed by a specialist before delivery. It's the document you
      can forward to your EU buyer.</p>
      <p><a href="https://trdrhub.com/tools/{'cbam' if tool == 'cbam' else 'eudr'}-readiness-check"
            style="color:#0f3d3e;font-weight:bold">Get the full readiness report →</a></p>
      <hr style="border:none;border-top:1px solid #dde">
      <p style="font-size:11px;color:#889">This scope check is an advisory indication, not legal
      advice, and not a formal scope determination. TRDR Hub · trdrhub.com</p>
    </div>
    """


# ---------------------------------------------------------------------------
# Paid engine — map intake answers to the RulHub m13 rule corpus
# ---------------------------------------------------------------------------

# Topic probes per tool: (answer_id, gap_values, search_query, requirement_title,
# what_the_reg_expects, suggested_fix). The engine searches the m13 corpus for
# each topic and cites the top rule(s); the customer's answer decides severity.
_CBAM_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "emissions_data",
        "gap": ("no",), "partial": ("partial",),
        "query": "CBAM embedded emissions calculation actual values installation",
        "title": "Embedded-emissions data for your EU-bound goods",
        "expected": "Installation-level direct (and for some goods indirect) embedded emissions, calculated per the CBAM methodology, reported per good.",
        "fix": "Set up emissions accounting per installation (fuel, electricity, precursor inputs) so your importer can declare actual values instead of punitive default values.",
    },
    {
        "id": "monitoring_system",
        "gap": ("no",), "partial": ("partial",),
        "query": "CBAM monitoring methodology verification accredited verifier",
        "title": "Monitoring plan and verification-ready records",
        "expected": "A documented monitoring methodology whose emissions figures an accredited verifier can verify.",
        "fix": "Adopt a monitoring plan (the EU's CBAM communication templates are a practical starting point) and keep records verification-ready.",
    },
    {
        "id": "carbon_price_paid",
        "gap": ("unsure",), "partial": (),
        "query": "CBAM carbon price paid country of origin deduction",
        "title": "Carbon price paid at origin — potential deduction",
        "expected": "A carbon price effectively paid in the country of production can reduce the CBAM certificates your importer must surrender — with documentary evidence.",
        "fix": "Confirm whether any carbon levy applies to your production and collect proof of payment; it directly lowers your buyer's CBAM cost.",
    },
    {
        "id": "buyer_requests",
        "gap": (), "partial": (),
        "query": "CBAM declarant reporting obligations annual declaration",
        "title": "Importer declaration timeline",
        "expected": "Your EU importer files an annual CBAM declaration (first one due 30 September 2027 for 2026 imports) built on your data.",
        "fix": "Agree a data-delivery schedule with each EU buyer ahead of their declaration deadline.",
    },
]

_EUDR_TOPICS: List[Dict[str, Any]] = [
    {
        "id": "supply_chain_visibility",
        "gap": ("no",), "partial": ("partial",),
        "query": "EUDR geolocation plot of land coordinates due diligence statement",
        "title": "Plot-level geolocation of production",
        "expected": "Geolocation coordinates for every plot of land where the commodity was produced — mandatory content of the buyer's due diligence statement.",
        "fix": "Map your supplying farms/plots (point coordinates; polygons for plots over 4 ha) and attach them to every consignment.",
    },
    {
        "id": "cutoff_evidence",
        "gap": ("no",), "partial": ("partial",),
        "query": "EUDR deforestation-free cutoff date 31 December 2020 evidence",
        "title": "Deforestation-free evidence against the 2020 cutoff",
        "expected": "Evidence that the production land was not deforested or degraded after 31 December 2020 (satellite imagery, certification, field verification).",
        "fix": "Assemble land-use evidence per plot — buyers increasingly cross-check coordinates against satellite deforestation alerts.",
    },
    {
        "id": "legality_docs",
        "gap": ("no",), "partial": ("partial",),
        "query": "EUDR legality legislation of country of production land use rights",
        "title": "Legality documentation for production",
        "expected": "Proof of production in accordance with the origin country's laws — land rights, environmental permits, labour and human-rights compliance.",
        "fix": "Compile the legality file per origin (titles/leases, permits, labour compliance) mapped to your plots.",
    },
    {
        "id": "traceability_system",
        "gap": ("no",), "partial": ("partial",),
        "query": "EUDR traceability supply chain information requirements",
        "title": "Traceability from plot to shipment",
        "expected": "The ability to connect each EU-bound consignment back to its production plots, including where commodities are mixed.",
        "fix": "Implement segregation or documented mass-balance so each shipment carries its plot list; unmixed lots are far easier to place.",
    },
]


async def _discover_source(client, keyword: str) -> Optional[str]:
    """Find the m13 rule source slug for a topic (e.g. 'cbam' → 'cbam_regulation')."""
    try:
        res = await client.lookup_rules(source=keyword, per_page=1)
        if res.get("results"):
            return res["results"][0].get("source") or keyword
    except Exception:
        pass
    try:
        res = await client.search_rules(query=keyword.upper(), per_page=10)
        for r in res.get("results", []):
            src = str(r.get("source") or "")
            if keyword.lower() in src.lower():
                return src
    except Exception:
        pass
    return None


def _finding(topic: Dict[str, Any], severity: str, answer_value: str,
             rules: List[Dict[str, Any]], tool: str) -> Dict[str, Any]:
    top = rules[0] if rules else {}
    citation = (top.get("text") or "").strip()
    rule_id = top.get("rule_id") or f"{tool.upper()}-{topic['id'].upper()}"
    article = top.get("article")
    refs = ", ".join(
        f"{r.get('rule_id')}" + (f" (Art. {r.get('article')})" if r.get("article") else "")
        for r in rules[:3] if r.get("rule_id")
    )
    status_word = {"critical": "GAP", "major": "GAP", "minor": "PARTIAL", "info": "IN PLACE"}[severity]
    return {
        "rule": rule_id,
        "rule_id": rule_id,
        "title": f"[{status_word}] {topic['title']}",
        "severity": severity,
        "message": topic["expected"],
        "expected": topic["expected"],
        "found": f"Your answer: {answer_value or '(not answered)'}",
        "suggested_fix": topic["fix"],
        "clause_cited": citation[:500] if citation else "",
        "ucp_reference": None,
        "isbp_reference": None,
        "regulation_refs": refs or None,
        "article": article,
        "document_type": "readiness_intake",
        "source_layer": "readiness_engine",
        "display_card": True,
    }


async def run_readiness_engine(tool: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """Map intake answers against the RulHub m13 corpus. Returns
    {"issues": [...], "engine_error": str|None, "rules_consulted": int}.

    Never raises — a RulHub outage still lets the job enter the review queue
    (findings empty + engine_error set; the operator re-runs via the admin
    rerun endpoint before delivery).
    """
    from app.services.rulhub_client import get_rulhub_client

    tools = ["cbam", "eudr"] if tool == "both" else [tool]
    issues: List[Dict[str, Any]] = []
    rules_consulted = 0
    engine_error: Optional[str] = None
    client = get_rulhub_client()

    for t in tools:
        topics = _CBAM_TOPICS if t == "cbam" else _EUDR_TOPICS
        source = None
        try:
            source = await _discover_source(client, "cbam" if t == "cbam" else "eudr")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("readiness source discovery failed for %s: %s", t, exc)

        for topic in topics:
            answer_value = str(answers.get(topic["id"]) or "")
            if answer_value in topic["gap"]:
                severity = "major"
            elif answer_value in topic.get("partial", ()):
                severity = "minor"
            else:
                severity = "info"

            rules: List[Dict[str, Any]] = []
            try:
                payload: Dict[str, Any] = {"query": topic["query"], "per_page": 3}
                if source:
                    payload["source"] = source
                res = await client.search_rules(**payload)
                rules = [r for r in res.get("results", []) if isinstance(r, dict)]
                rules_consulted += len(rules)
            except Exception as exc:
                engine_error = f"RulHub rule lookup failed: {str(exc)[:200]}"
                logger.warning("readiness engine search failed (%s/%s): %s", t, topic["id"], exc)

            issues.append(_finding(topic, severity, answer_value, rules, t))

    if engine_error:
        logger.warning("readiness engine finished degraded: %s", engine_error)
    return {"issues": issues, "engine_error": engine_error, "rules_consulted": rules_consulted}
