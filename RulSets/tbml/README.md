# TBML v1 Deterministic Rulepack

This folder contains the first production-ready deterministic TBML seed rules for TRDR Hub.

## Rule counts by file
- tbml_pricing_anomaly.json: 8 rules
- tbml_quantity_weight_mismatch.json: 8 rules
- tbml_route_logistics_anomaly.json: 8 rules
- tbml_counterparty_network_risk.json: 8 rules
- tbml_document_behavioral_signals.json: 8 rules
- tbml_sanctions_pep_enhanced.json: 10 rules
- **Total: 50 deterministic rules**

## Scoring intent
- **fail**: hard-stop indicators likely tied to TBML, sanctions, or material documentation contradictions.
- **warn**: risk amplifiers requiring analyst review / enhanced due diligence but not immediate rejection by default.
- Every rule is deterministic (deterministic=true) and non-LLM (equires_llm=false) to ensure consistent repeatable scoring.

## Upload / activate
1. Open Ruleset uploader in TRDR Hub admin.
2. Upload each JSON in this folder under the correct domain bucket (recommended domain: 	bml.v1).
3. Verify parser acceptance (severity in ail|warn|info, conditions array present, expected_outcome object present).
4. Publish/activate the new TBML ruleset version.
5. Run a dry validation on recent trade files and review hit rates before full enforcement.
