"""
Prototype: AI Examiner — proof of concept.

Reads IDEAL SAMPLE PDFs + LC, runs a single Sonnet call with the
constrained prompt (LC text = only rulebook, every finding must cite
verbatim LC text + verbatim doc text), applies the substring
verification filter, prints findings for review.

Standalone. Does not touch the deployed pipeline.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests

IDEAL = Path(r"H:/.openclaw/workspace/trdrhub.com/.playwright-mcp/ideal-sample")

DOC_MAP = {
    "LC.pdf": "letter_of_credit",
    "Invoice.pdf": "invoice",
    "Bill_of_Lading.pdf": "bill_of_lading",
    "Packing_List.pdf": "packing_list",
    "Certificate_of_Origin.pdf": "certificate_of_origin",
    "Inspection_Certificate.pdf": "inspection_certificate",
    "Insurance_Certificate.pdf": "insurance_certificate",
    "Beneficiary_Certificate.pdf": "beneficiary_certificate",
}


def load_env():
    env = {}
    p = Path(r"H:/.openclaw/workspace/trdrhub.com/apps/api/.env")
    for line in p.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def pdf_to_text(pdf_path):
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def load_docs():
    lc_text = ""
    docs = {}
    for filename, doc_type in DOC_MAP.items():
        p = IDEAL / filename
        if not p.exists():
            continue
        text = pdf_to_text(p)
        if doc_type == "letter_of_credit":
            lc_text = text
        else:
            docs[doc_type] = text
    return lc_text, docs


SYSTEM_PROMPT = """You are a senior trade-finance examiner reviewing a documentary credit presentation.
Your job is to identify discrepancies that would cause a bank to reject or query the submission.

THE RULEBOOK
============
The Letter of Credit text is your ONLY rulebook. Every compliance-bearing clause applies —
amounts, dates, ports, parties, shipment terms, tolerances, goods descriptions, documents
required, additional conditions, presentation period, and any other field present.

You CANNOT cite UCP600 articles from memory. You CANNOT reference rules you recall from training.
Every finding must be grounded in this specific LC's verbatim text.

THINK LIKE AN EXAMINER, NOT A CHECKLIST
========================================

1. SUBSTANCE OVER FORM.
   Bank examiners reject on substantive discrepancies (wrong amount, missing party, missing
   notation the LC demands, wrong port, unsigned signature block). They do NOT reject on
   physical-presentation artifacts that cannot be verified from extracted text:
     - "in N copies" — copy counts are a physical-handling concern, not evidenced in extracted text
     - Paper original vs electronic original — not evidenced in extracted text
     - Whether non-negotiable copies were couriered to the applicant within N days — a future
       process step, not a discrepancy in the present submission
   Skip clauses whose satisfaction cannot be judged from the document text you have.

2. READ FOR INTENT, NOT KEYWORD-MATCH.
   "USD 7.20" on a line showing "30,000 pcs" unambiguously means per piece — don't flag it as
   "unit price not clear". Well-known port aliases (e.g. Chittagong ↔ Chattogram, Bombay ↔
   Mumbai) refer to the same place — flag only if the examiner would treat it as a real
   mismatch. Use common sense. A human examiner would let small cosmetic variance pass.

3. DO THE ARITHMETIC.
   When the invoice has line items with quantity and unit price, compute Σ(quantity × unit
   price) and compare to the stated total. Any gap beyond a rounding floor is a major
   discrepancy. Do the same for weights across BL / packing list, totals across multiple
   invoices, tolerance ranges on quantities. Compute; don't just assert.

4. CHECK DATES AND CHRONOLOGY.
   Every document date should fit the window the LC defines (issue date through expiry, with
   latest-shipment-date as a key cutoff). Dates referenced across documents (e.g. BL shipment
   date vs inspection cert shipment date) should be consistent. Flag actual date conflicts,
   not formatting differences.

5. BE INTERNALLY CONSISTENT. READ YOUR OWN REASONING BEFORE EMITTING.
   A finding's reasoning must CONFIRM the discrepancy, not walk it back.
   BEFORE adding any finding to the output, ask yourself: "Does my reasoning say the document
   is compliant, fine, consistent, or within limits?" If yes — DELETE the finding entirely.
   Do not emit it with a contradictory reasoning.

   FORBIDDEN PATTERNS in your reasoning field (drop the finding if you find yourself writing
   any of these):
     - "so this is compliant"
     - "is compliant"
     - "appears compliant"
     - "this is fine"
     - "no discrepancy"
     - "within the allowed"
     - "is consistent"
     - "is within"

   A finding is only valid if its reasoning clearly ESTABLISHES the problem. If after thinking
   it through the document is actually fine, that is a successful examination — silence, not
   a finding. You are not rewarded for finding count; you are rewarded for accuracy.

6. EVIDENCE IS MANDATORY.
   Every finding must cite:
     - `clause_cited`: verbatim substring from the LC establishing the requirement (longer is
       better — prefer 10+ tokens of context).
     - `found_evidence`: verbatim substring from the specific supporting document showing the
       problem, OR the exact string "ABSENT" when the expected item is not present at all.
   No citation, no finding. If you cannot quote the LC clause verbatim, silence is correct.

7. WHEN IN DOUBT, SKIP.
   A false positive costs more than a silent miss — it trains the operator to distrust the
   system. Only raise a finding when a reasonable examiner would raise it. If you're unsure
   whether a clause applies, or whether the document text supports the finding, do not emit it.

SEVERITY
========
- `critical`: blocking — bank will reject on sight (wrong amount, missing required document
  entirely, wrong parties, dates outside LC window, BL missing essential clean-on-board
  notation, unsigned document that the LC requires signed).
- `major`: likely query — examiner will raise a discrepancy note (arithmetic gap, missing
  specific wording the LC demands, cross-doc data conflict, missing carton-wise detail when
  LC explicitly requires it).
- `minor`: advisory — document acceptable but noteworthy (known port-name aliases, extraneous
  documents not required by this LC, minor formatting).

OUTPUT SCHEMA
=============
{
  "findings": [
    {
      "rule_id": "EXAMINER-<short-slug>",
      "severity": "critical" | "major" | "minor",
      "document": "<doc_type from the supporting-docs set>",
      "title": "<one-line summary of the discrepancy>",
      "clause_cited": "<verbatim LC substring establishing the requirement>",
      "expected": "<plain-language description of what the LC requires>",
      "found_evidence": "<verbatim doc substring showing the problem, or 'ABSENT'>",
      "reasoning": "<one sentence explaining why this is a discrepancy; must not contradict the title>"
    }
  ],
  "overall_assessment": "<one-sentence summary>"
}

Return JSON only, no prose.
"""


def build_prompt(lc_text, docs):
    parts = [
        "## LETTER OF CREDIT (full text — your rulebook)",
        "```",
        lc_text.strip(),
        "```",
        "",
        "## SUPPORTING DOCUMENTS",
    ]
    for doc_type, text in docs.items():
        parts.append(f"\n### {doc_type}")
        parts.append("```")
        parts.append(text.strip())
        parts.append("```")
    parts.append("\n\nExamine every supporting document against every compliance-bearing LC field. List discrepancies.")
    return "\n".join(parts)


def call_sonnet(env, system, user, model="anthropic/claude-sonnet-4-5-20250929"):
    key = env.get("OPENROUTER_API_KEY")
    url = env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/chat/completions"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://trdrhub.com",
            "X-Title": "trdrhub examiner prototype",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return content, usage


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    return None


def normalize_whitespace(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


_SELF_CONTRADICTING_PHRASES = (
    "so this is compliant",
    "is compliant",
    "appears compliant",
    "this is fine",
    "no discrepancy",
    "within the allowed",
    " is consistent",
    "is within the",
    "is compliant with",
    "no issue",
    "this is acceptable",
    "no violation",
)


def is_self_contradicting(finding):
    """Detect findings whose reasoning walks back the title. These are
    cases where the LLM flagged something, then concluded it's actually
    fine — but emitted the finding anyway. We drop those deterministically.
    """
    reasoning = (finding.get("reasoning") or "").lower()
    if not reasoning:
        return False
    return any(phrase in reasoning for phrase in _SELF_CONTRADICTING_PHRASES)


def verify_findings(findings, lc_text, docs):
    """Apply the verification filters:
    1. Substring citation verification (hallucination guard).
    2. Self-contradiction filter (reasoning walks back the title).
    """
    lc_norm = normalize_whitespace(lc_text)
    docs_norm = {dt: normalize_whitespace(t) for dt, t in docs.items()}
    survivors = []
    dropped = []
    for f in findings:
        clause = f.get("clause_cited") or ""
        doc = f.get("document") or ""
        found_ev = f.get("found_evidence") or ""

        # (1) Clause must be a verbatim substring of LC
        clause_norm = normalize_whitespace(clause)
        if not clause_norm or clause_norm not in lc_norm:
            dropped.append((f.get("rule_id", "?"), f"clause_cited not in LC: {clause[:80]!r}"))
            continue

        # (2) Evidence must be a verbatim substring of the named doc (unless ABSENT)
        if found_ev.strip().upper() != "ABSENT":
            ev_norm = normalize_whitespace(found_ev)
            doc_norm = docs_norm.get(doc)
            if doc_norm is None:
                dropped.append((f.get("rule_id", "?"), f"unknown document: {doc!r}"))
                continue
            if not ev_norm or ev_norm not in doc_norm:
                dropped.append((f.get("rule_id", "?"), f"found_evidence not in {doc}: {found_ev[:80]!r}"))
                continue

        # (3) Reasoning must not walk back the title
        if is_self_contradicting(f):
            dropped.append((
                f.get("rule_id", "?"),
                f"self-contradicting reasoning: {(f.get('reasoning') or '')[:120]!r}",
            ))
            continue

        survivors.append(f)
    return survivors, dropped


def main():
    env = load_env()
    if not env.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set in apps/api/.env", file=sys.stderr)
        sys.exit(1)

    print("Loading docs...")
    lc_text, docs = load_docs()
    print(f"  LC: {len(lc_text)} chars")
    for dt, t in docs.items():
        print(f"  {dt}: {len(t)} chars")

    print("\nBuilding prompt...")
    user_prompt = build_prompt(lc_text, docs)
    print(f"  User prompt: {len(user_prompt)} chars")

    model = sys.argv[1] if len(sys.argv) > 1 else "anthropic/claude-sonnet-4-5-20250929"
    print(f"\nCalling {model}...")
    try:
        raw, usage = call_sonnet(env, SYSTEM_PROMPT, user_prompt, model=model)
    except requests.HTTPError as e:
        print(f"HTTPError: {e}\n{e.response.text[:2000]}")
        sys.exit(1)

    print(f"\nTokens: in={usage.get('prompt_tokens')}, out={usage.get('completion_tokens')}")
    print("\n--- RAW RESPONSE ---")
    print(raw[:5000])
    print("--- END RAW ---\n")

    parsed = extract_json(raw)
    if not parsed:
        print("ERROR: could not parse JSON from response.")
        sys.exit(1)

    findings = parsed.get("findings", [])
    print(f"\nLLM claimed {len(findings)} findings:")
    for i, f in enumerate(findings):
        print(f"  [{i}] {f.get('severity','?'):6} | {f.get('document','?'):28} | {f.get('title','')[:90]}")

    print("\n--- APPLYING SUBSTRING VERIFICATION FILTER ---")
    survivors, dropped = verify_findings(findings, lc_text, docs)
    if dropped:
        print(f"\n{len(dropped)} findings DROPPED (hallucinations / unverifiable):")
        for rid, why in dropped:
            print(f"  - {rid}: {why}")

    print(f"\n{len(survivors)} SURVIVING findings:")
    for i, f in enumerate(survivors):
        print(f"\n  [{i}] {f.get('severity','?')} | {f.get('rule_id','?')}")
        print(f"       doc:            {f.get('document','?')}")
        print(f"       title:          {f.get('title','?')}")
        print(f"       clause_cited:   {f.get('clause_cited','')[:200]!r}")
        print(f"       expected:       {f.get('expected','?')}")
        print(f"       found_evidence: {f.get('found_evidence','')[:200]!r}")
        print(f"       reasoning:      {f.get('reasoning','?')}")

    print(f"\nOverall: {parsed.get('overall_assessment','(none)')}")


if __name__ == "__main__":
    main()
