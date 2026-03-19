# Public Beta Scope

## In scope

- exporter upload, validation, results, history, and repeat-use loop
- importer upload and review flow on the same backend and frontend result spine
- one canonical validation payload and one canonical results contract
- deterministic login, onboarding, and dashboard routing
- hard paywall with an initial free-check or free-token allowance
- English-only public beta operations

## Conditional secondary scope

The following surfaces may remain visible only if they reuse the same stabilized auth, validation, and result spine:

- combined dashboard
- enterprise dashboard
- workspace and side-productivity surfaces

If any of these introduce conflicting auth or result behavior, they should be hidden or deprioritized before beta.

## Parked for this beta

- bank as a launch-critical user journey
- bank launch readiness and bank-specific release criteria
- separate importer-only architecture or payload logic
- broad feature expansion that does not improve trust in the core loop

## Beta success criteria

The beta is ready to open when:

- exporter is trustworthy end to end
- importer rides the same shared core without forking behavior
- auth, onboarding, and routing no longer send users to the wrong place
- `structured_result` is stable enough that the frontend can render without contradictory fallback state
- paywall and quota behavior are predictable
