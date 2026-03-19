# LCopilot User Flows

This document describes the current beta-facing user journeys.

## Canonical beta truth

- LCopilot ships as one product spine.
- Exporter is the gold path.
- Importer is real, but secondary to exporter and built on the same core.
- Bank is parked from launch-critical beta scope.

## 1. Exporter flow

Exporter is the reference user journey for beta.

Target flow:

1. login
2. land on exporter dashboard
3. upload LC-related documents
4. run validation
5. review persisted results
6. reopen through history later
7. hit quota or paywall when appropriate
8. repeat

Everything else in beta should be measured against how well this path works.

## 2. Importer flow

Importer is in scope, but it should not become a second architecture.

Target flow:

1. login
2. land on importer dashboard
3. upload draft or import-side LC documents
4. run the same validation pipeline
5. review the same canonical result contract
6. reopen through the same history path

Importer should differ in framing and actions, not in backend truth.

## 3. Combined and enterprise

The repo contains combined and enterprise surfaces.

For beta:

- they are secondary, not defining
- they should remain visible only if they reuse the same auth, validation, and results spine
- they should not introduce a parallel product definition

## 4. Bank

Bank remains in the codebase, but it is not part of the launch-critical public beta path.

Implication:

- do not let bank-specific scope drive beta routing or release criteria
- keep bank docs and bank launch materials as supporting historical references, not canonical beta truth

## 5. Launch discipline

If a user flow competes with exporter trust, importer convergence, auth stability, or canonical results, it should be cut or demoted before beta opens.
