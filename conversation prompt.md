  Diagnostic narrowing

  Where the 500 came from (certain): the response carried reference_id, which only validate_internal_error_handler
  (app/services/validate_error_handlers.py:94) injects. That handler catches unhandled Exception — so the failure is a Python       
  exception escaping the route, NOT a Schema B violation (those come back as structured 400) and NOT a Pydantic body-parse error    
  (also structured 400 via validate_request_validation_error).

  Code paths in validate_set_v1 (app/routers/validate_v1.py:603–795) that can raise unhandled Exception:

  ┌─────────────────────────────────────────────────────────┬───────┬──────────────────────────────────────────────────────────┐    
  │                          Site                           │ Line  │                     Why it's likely                      │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ filter_applicable_rules(all_rules, envelope)            │ 681   │ path-extraction logic on weird envelope shapes           │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ convert_rule_to_conditions(raw_conditions)              │ 703   │ malformed rule payload from DB                           │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ validate_conditions(envelope, conditions)               │ 709   │ highest-probability — 30+ validator dispatch, prone to   │    
  │                                                         │       │ per-validator KeyError/AttributeError                    │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ _build_finding(ctype, details) /                        │ 739,  │ template formatting on unexpected details shapes         │    
  │ _build_recommendation(ctype, details)                   │ 745   │                                                          │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ db.commit() / db.refresh()                              │ 775,  │ Postgres deadlock / connection issue                     │    
  │                                                         │ 776   │                                                          │    
  ├─────────────────────────────────────────────────────────┼───────┼──────────────────────────────────────────────────────────┤    
  │ ValidationLog(...) field shape mismatch                 │ 767   │ result={"score":..., "discrepancies": int} written to a  │    
  │                                                         │       │ column                                                   │    
  └─────────────────────────────────────────────────────────┴───────┴──────────────────────────────────────────────────────────┘    

  The rules-fetch try/except (line 660) wraps in HTTPException(500) with a plain detail string — that path produces a 500 without   
  reference_id. So that's NOT what trdrhub hit.

  The "1 doc" paradox

  If trdrhub really sent 1 document to /v1/validate/set, both Pydantic (min_length=2 on documents, line 557) AND Schema B (minItems:   2) would emit a structured 400 — never a 500. Two options:

  a. The ref=0a9d75ca74cd payload wasn't actually 1 doc (the trdrhub-side description was loose). It's likely 2+ where one is a     
  placeholder/empty draft.
  b. trdrhub is calling /v1/validate (single) not /v1/validate/set, and the report misnamed it.

  Either way, the min_length=2 constraint is enforced at Pydantic 2.11.9.

  What I need to actually pin it

  Given Sentry isn't reachable from this session (no Render/Sentry MCP wired into rulhub Claude), one of:

  1. Sentry stack trace. Both refs are tagged rulhub.reference_id=<id> and rulhub.endpoint=/v1/validate/set. Sentry search:
  tags["rulhub.reference_id"]:0a9d75ca74cd OR tags["rulhub.reference_id"]:77a432e2c6c4. Paste the top frame here.
  2. The actual JSON body trdrhub sent for either ref (sanitized — keep the doc-type keys + field names intact, blank out values).  
  One body is enough.
  3. Render log slice for the timestamp of either 500. With validate_internal_error endpoint=/v1/validate/set
  reference_id=0a9d75ca74cd log line, the immediately following stack trace prints from logger.exception.

  Surface back to the trdrhub session

  ▎ rulhub Claude here, code-side analysis on the two refs:
  ▎
  ▎ - The 500s came through the unhandled-exception handler (only path that emits reference_id), so this is a Python exception      
  ▎ escaping the /v1/validate/set route. Most likely site (~70%): validate_conditions blowing up on a specific validator type given 
  ▎ your envelope shape. Other candidates: filter_applicable_rules, _build_finding template, or a DB write timeout on db.commit().  
  ▎ - The min_length=2 / minItems:2 constraint on documents is enforced (Pydantic 2.11.9). A genuine 1-doc payload would 400,       
  ▎ not 500. So ref=0a9d75ca74cd is either 2+ docs in reality or hit /v1/validate instead of /v1/validate/set — please double-check 
  ▎ the workflow_type=importer_draft_lc mapping.
  ▎ - To unblock fix on rulhub side I need ONE of: (a) Sentry stack trace under either ref, (b) the actual sanitized JSON body for  
  ▎ one of the refs, (c) the Render log slice with logger.exception output around the ref. Without one of those I'm guessing at a   
  ▎ 30-validator surface.
  ▎ - Permanent improvement on your side: capture detail.reference_id AND log the request body (sanitized) into your
  ▎ _db_rules_debug.rulhub_error so the next 500 is single-shot diagnosable. You're already 90% there with the ref capture — adding 
  ▎ the request body closes the loop.
