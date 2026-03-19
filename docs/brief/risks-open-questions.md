# Risks & Open Questions

## Highest launch risks

### 1. Auth, onboarding, and routing trust

This is the largest launch blocker in the repo.

Failure mode:

- users land on the wrong dashboard
- stale session data leaks across logins
- different dashboards use different auth assumptions

### 2. Result-contract drift

The frontend and backend still carry compatibility and fallback logic.

Failure mode:

- the UI appears to work while rendering contradictory or stale state
- exporter and importer drift away from the persisted backend truth

### 3. Exporter and importer divergence

The product will slip if importer becomes a separate execution lane instead of converging onto exporter's shared spine.

### 4. Commercial gating friction

The beta includes a hard paywall with an initial free-entry allowance.

Failure mode:

- users hit gating before trust is established
- backend and frontend quota behavior diverge

### 5. Secondary-surface distraction

Combined, enterprise, workspace, and bank surfaces can absorb time without improving beta trust in the core loop.

## Open questions still requiring business confirmation

- final free-check or free-token allowance
- final pricing and packaging
- whether combined and enterprise remain visible if they cannot stay on the same stabilized spine
- whether importer scope compresses if parity requires branching away from exporter infrastructure
