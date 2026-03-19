# Executive Summary

LCopilot is a trade-document validation product for SMEs, MSMEs, and small trade-finance operators who need faster, more trustworthy LC review.

The public beta ships one product spine with two real user journeys:

- Exporter: primary launch path and deepest surface
- Importer: real beta path built on the same shared core

Bank is present in the codebase but is parked from launch-critical scope.

The product promise for beta is simple:

- upload LC-related documents
- extract and validate them through the shared validation core
- return a trustworthy results payload with explainable issues and readiness signals
- let users come back to those results later through the same persisted contract

What matters most in this beta is not adding more surfaces. It is making the existing validation, results, and routing loop trustworthy enough that users can rely on it.

The execution priorities follow directly from that truth:

- protect exporter as the gold path
- converge importer onto the same auth and result spine
- freeze `structured_result` and `GET /api/results/{jobId}` as canonical result truth
- remove auth, onboarding, and routing contradictions before opening beta
