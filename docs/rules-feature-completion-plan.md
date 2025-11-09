# Rules Feature Completion Plan

## Current Status Summary

**Phase 0**: ✅ Complete - Standards and shapes defined, JSON schemas in repo
**Phase 1**: ⚠️ Partial - Storage bucket + tables created, RLS policies missing
**Phase 2**: ✅ Complete - All API endpoints implemented
**Phase 3**: ⚠️ Partial - Rulesets list + Upload UI done, "Active" view missing
**Phase 4**: ❌ Not Started - RulesService + RuleEvaluator + Integration needed
**Phase 5**: ⚠️ Partial - Audit logging done, analytics/metrics missing

## Remaining Work

### Phase 1 Completion: RLS Policies

**File**: SQL migration to be applied via Supabase MCP

**Actions**:
1. Enable RLS on `rulesets` table
2. Enable RLS on `ruleset_audit` table
3. Create policies:
   - `rule:read` → SELECT on active rulesets (public)
   - `rule:write` → INSERT/UPDATE on rulesets (admin only)
   - `rule:publish` → UPDATE status to 'active' (admin only)
   - Admin service role bypasses RLS for API operations

**SQL**:
```sql
ALTER TABLE rulesets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ruleset_audit ENABLE ROW LEVEL SECURITY;

-- Public read access to active rulesets
CREATE POLICY "public_read_active_rulesets" ON rulesets
  FOR SELECT USING (status = 'active');

-- Admin full access
CREATE POLICY "admin_full_access_rulesets" ON rulesets
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM users 
      WHERE users.id = auth.uid() 
      AND users.role IN ('admin', 'super_admin')
    )
  );

-- Audit logs: admin read only
CREATE POLICY "admin_read_audit" ON ruleset_audit
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM users 
      WHERE users.id = auth.uid() 
      AND users.role IN ('admin', 'super_admin')
    )
  );
```

### Phase 3 Completion: Active Ruleset View

**File**: `apps/web/src/pages/admin/sections/rules/Active.tsx` (new)

**Actions**:
1. Create `Active.tsx` component showing active rulesets per domain/jurisdiction
2. Display cards/table with: Domain, Jurisdiction, Rulebook Version, Rules Count, Published Date
3. Add "Download JSON" button per active ruleset (uses signed URL from API)
4. Add to AdminShell routing (`rules-active` section)
5. Add to AdminSidebar navigation

**Key Features**:
- Fetches active rulesets via `service.getActiveRuleset(domain, jurisdiction)`
- Shows download button that triggers signed URL fetch
- Displays "No active ruleset" message for empty domains
- Filter by domain/jurisdiction dropdowns

### Phase 4: RulesService Interface & LocalAdapter

**File**: `apps/api/app/services/rules_service.py` (new)

**Interface**:
```python
class RulesService:
    async def get_active_ruleset(
        self, domain: str, jurisdiction: str = "global"
    ) -> Dict[str, Any]:
        """Returns active ruleset with rules array"""
    
    async def evaluate_rules(
        self, rules: List[Dict], input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluates rules against document context"""
```

**LocalAdapter Implementation**:
- Fetches from Supabase via `get_active_ruleset` API endpoint
- In-memory cache with TTL (5-10 minutes)
- Cache key: `{domain}:{jurisdiction}`
- Cache invalidation on publish (webhook or manual)

**File**: `apps/api/app/services/rules_storage.py` (exists, may need updates)

### Phase 4: RuleEvaluator

**File**: `apps/api/app/services/rule_evaluator.py` (new)

**Actions**:
1. Implement condition evaluation:
   - Field path resolution (dot notation: `lc.goods_description`)
   - Operator handling: `equals`, `not_equals`, `contains`, `matches`, `within_days`, `before`, `after`, `in`, `not_in`, `exists`, `not_exists`
   - `value` vs `value_ref` handling
   - `day_type` support (`banking` vs `calendar`)
2. Implement `applies_if` preconditions
3. Implement `conditions` array evaluation (all must pass)
4. Return structured violations with rule_id, severity, message

**Key Logic**:
- Resolve field paths from nested document structure
- Handle date arithmetic for `within_days` with `day_type`
- Support `value_ref` to compare two fields
- Return `expected_outcome.valid` or `expected_outcome.invalid` messages

### Phase 4: Integration into Validation Flow

**File**: `apps/api/app/services/validator.py` (modify)

**Current Flow**:
- Uses `Rule` model or Rulhub API
- Simple condition evaluation

**New Flow**:
1. Check feature flag: `USE_JSON_RULES` (default: false for backward compat)
2. If enabled:
   - Fetch active ruleset via `RulesService.get_active_ruleset("icc", "global")`
   - Filter rules by `document_type` (e.g., "lc")
   - Evaluate via `RuleEvaluator.evaluate_rules()`
   - Merge results with existing validation
3. Record `ruleset_version` in validation results

**Integration Points**:
- `validate_document()` function in `validator.py`
- `RulesEngine.validate_session()` in `rules/engine.py` (optional, for session-based validation)
- `EnhancedLCValidator.validate_lc_document()` in `pipeline/validator.py` (optional)

**File**: `apps/api/app/routers/rules_admin.py` (modify)

**Add Cache Invalidation**:
- On `publish_ruleset()`: Clear cache for that domain/jurisdiction
- Add webhook endpoint: `POST /admin/rulesets/webhook/invalidate-cache` (internal)

### Phase 5: Analytics & Metrics

**File**: `apps/api/app/models/ruleset.py` (modify)

**Add Tracking Table** (optional, Phase 5 enhancement):
```python
class RuleHitLog(Base):
    """Tracks rule evaluations for analytics"""
    __tablename__ = "rule_hit_logs"
    id = Column(UUID, primary_key=True)
    ruleset_id = Column(UUID, ForeignKey("rulesets.id"))
    rule_id = Column(String)
    session_id = Column(UUID, nullable=True)
    hit = Column(Boolean)  # True if rule passed, False if failed
    evaluated_at = Column(DateTime(timezone=True))
```

**File**: `apps/web/src/pages/admin/sections/rules/Analytics.tsx` (new, optional)

**Display**:
- Top failing rules (rule_id, failure count)
- Rule hit rates per ruleset
- Most evaluated rules
- Dead rules (never evaluated)

## Implementation Order

1. **Phase 1**: Add RLS policies (SQL via Supabase MCP)
2. **Phase 3**: Create Active view page
3. **Phase 4**: Create RulesService + LocalAdapter
4. **Phase 4**: Create RuleEvaluator
5. **Phase 4**: Integrate into validation flow (with feature flag)
6. **Phase 4**: Add cache invalidation
7. **Phase 5**: Add analytics (optional, can defer)

## Testing Strategy

1. **Unit Tests**:
   - RuleEvaluator condition evaluation
   - Field path resolution
   - Operator handling (all operators)
   - `value_ref` resolution

2. **Integration Tests**:
   - RulesService cache behavior
   - API endpoint fetching active ruleset
   - Validation flow with JSON rules enabled

3. **Manual Testing**:
   - Upload UCP600 ruleset
   - Publish ruleset
   - Validate LC document
   - Verify rules are applied
   - Check cache invalidation on publish

## Rollout Plan

1. **Phase 1-3**: Deploy immediately (no breaking changes)
2. **Phase 4**: Deploy behind feature flag `USE_JSON_RULES=false`
3. **Testing**: Enable flag for test environment, validate with SMEs
4. **Production**: Enable flag gradually (canary deployment)
5. **Phase 5**: Deploy analytics after Phase 4 is stable

## Notes

- Keep backward compatibility: existing `Rule` model validation continues to work
- Feature flag allows gradual rollout
- Cache TTL can be adjusted based on performance needs
- Analytics can be added incrementally without blocking core functionality

