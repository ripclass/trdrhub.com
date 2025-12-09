# Active Context - December 2024

## Current Focus
LCopilot V1 Enhancement - Contract Validation + 47A Parser Debug

## Recent Work

### Phase 3: 47A Parser Debug (COMPLETED)
Fixed 47A Additional Conditions extraction issues across multiple extraction pipelines.

**Root Causes Found:**
1. AI extractors (primary path) didn't include `additional_conditions` in their prompts
2. Parser patterns were too restrictive for some LC formats
3. `structured_lc_builder.py` only looked for `clauses` key, not `additional_conditions`

**Files Modified:**
- `apps/api/app/services/extraction/clauses_47a_parser.py` - Added 7 patterns (up from 4), enhanced diagnostic logging
- `apps/api/app/services/extraction/ai_lc_extractor.py` - Added `additional_conditions` to extraction prompt
- `apps/api/app/services/extraction/ensemble_extractor.py` - Added `additional_conditions` to extraction prompt  
- `apps/api/app/services/extraction/structured_lc_builder.py` - Now checks `additional_conditions`, `clauses`, and `clauses_47a`
- `apps/api/app/routers/validate.py` - Enhanced 47A debug logging

**47A Parser Patterns (7 total):**
1. SWIFT `:47A:content` - MT700 format
2. `47A Additional Conditions` - Traditional format
3. `ADDITIONAL CONDITIONS` header - Generic
4. `Field 47A:` - Scanned PDFs
5. `47A\n` with content on next line - Bank PDFs
6. `47A:` catch-all - Simple format
7. `ADDL CONDS` - Abbreviated format

**Item Extraction Methods:**
- Numbered items: `1)`, `2)`, etc.
- Letter items: `a)`, `b)`, etc.
- Dash/bullet items: `-`, `•`
- Semicolon-separated
- Newline-separated
- Whole block fallback

### Phase 1: Contract Validation Layer (COMPLETED)
Implemented Output-First validation layer.

**Files Created/Modified:**
- `apps/api/app/services/validation/response_contract_validator.py` (NEW)
- `apps/api/app/services/validation/__init__.py` (updated exports)
- `apps/api/app/routers/validate.py` (added validation call)
- `apps/web/src/types/lcopilot.ts` (added ContractWarning types)
- `apps/web/src/lib/exporter/resultsMapper.ts` (extract warnings from response)
- `apps/web/src/pages/ExporterResults.tsx` (Alert component in Overview)

## Next Steps
### Phase 2: V1 Tab Cleanup
- Remove "Extracted Data" tab (merge into Documents with drawer)
- Remove "Submission History" tab (move to Customs Pack)
- Remove "Analytics" tab (merge into Overview with progress bars)
- Update `dashboardTabs.ts` to reflect 4-tab structure

## Architecture Notes

### 47A Extraction Flow
```
OCR Text → AI Extractor → additional_conditions array
              ↓                    ↓
         Regex Parser → clauses_47a_parser.py
              ↓                    ↓
       structured_lc_builder → lc_structured.additional_conditions
              ↓
       _build_lc_baseline_from_context → baseline._conditions_list
              ↓
       Contract Validator → Warning if empty
```

### Contract Validation Flow
```
Backend Processing → Contract Validation → Response
                           ↓
                    _contract_warnings[]
                           ↓
                    Frontend mappers
                           ↓
                    Overview Alert UI
```

### Warning Severity Levels
- `error`: Critical field missing (may cause downstream failures)
- `warning`: Recommended field missing (functionality degraded)
- `info`: Optional field missing (noted for completeness)

