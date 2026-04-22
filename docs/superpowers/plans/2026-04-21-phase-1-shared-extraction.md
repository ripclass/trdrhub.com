# Phase 1 — Shared Component Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor exporter-specific UI primitives into `apps/web/src/components/lcopilot/` as a shared home, with zero behavior change. Foundation for Phases 2-4.

**Architecture:** Pure move-and-rename refactor of 7 pieces. Exporter keeps working identically. Each piece is extracted in its own commit so regressions bisect cleanly. Playwright regression on `tests/e2e/lcopilot/exporter-validation.spec.ts` runs before AND after each extraction.

**Tech Stack:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui. Vitest for unit, Playwright for e2e. All files under `apps/web/src/`.

**Spec:** `docs/superpowers/specs/2026-04-21-importer-parity-design.md` (Phase 1 section)

---

## Pre-flight

### Task 0: Establish baseline and workspace

**Files:**
- Modify: none (read-only recon)

- [ ] **Step 1: Verify exporter baseline green**

Run:
```
cd apps/web && npm run type-check && npm run lint && npm run test
```
Expected: all three pass clean. If any fails, STOP — fix baseline before starting refactor.

- [ ] **Step 2: Capture Playwright baseline snapshot**

Run:
```
cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts --reporter=json > /tmp/phase1-baseline.json
```
Expected: JSON file with passing test results. Save this — we'll diff after each extraction commit.

- [ ] **Step 3: Confirm target directory exists**

Run:
```
ls apps/web/src/components/lcopilot/
```
Expected: directory exists (already contains `ExporterSidebar.tsx`, `ExporterDashboardLayout.tsx`, etc.). If missing, `mkdir -p apps/web/src/components/lcopilot`.

- [ ] **Step 4: Identify all existing referrers for each target piece**

Run:
```
cd apps/web/src && grep -rn "from.*ExtractionReview" . --include="*.ts" --include="*.tsx" | head -20
grep -rn "from.*resultsMapper" . --include="*.ts" --include="*.tsx" | head -20
grep -rn "from.*VerdictTab\|DocumentsTab\|FindingsTab\|HistoryTab" . --include="*.ts" --include="*.tsx" | head -20
grep -rn "from.*PreparationGuide" . --include="*.ts" --include="*.tsx" | head -20
```
Write the findings into a scratch file `/tmp/phase1-referrers.txt` — each extraction task will re-grep but this gives you the scope up front.

- [ ] **Step 5: No commit (recon only)**

---

## Task 1: Extract ExtractionReview

**Files:**
- Move: `apps/web/src/pages/exporter/ExtractionReview.tsx` → `apps/web/src/components/lcopilot/ExtractionReview.tsx`
- Modify: all importers of `ExtractionReview`

- [ ] **Step 1: Find all referrers**

Run:
```
cd apps/web/src && grep -rln "pages/exporter/ExtractionReview\|exporter/ExtractionReview" . --include="*.ts" --include="*.tsx"
```
Expected: list of files (typically `ExportLCUpload.tsx`). Note them.

- [ ] **Step 2: Move the file**

Run:
```
git mv apps/web/src/pages/exporter/ExtractionReview.tsx apps/web/src/components/lcopilot/ExtractionReview.tsx
```

- [ ] **Step 3: Update every referrer's import path**

For each file found in Step 1, replace:
```
from "@/pages/exporter/ExtractionReview"    →    from "@/components/lcopilot/ExtractionReview"
from "./ExtractionReview" (if co-located)   →    from "@/components/lcopilot/ExtractionReview"
```

Use exact search-replace. Do not rename the default export.

- [ ] **Step 4: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS (zero errors).

- [ ] **Step 5: Unit tests**

Run: `cd apps/web && npm run test`
Expected: PASS.

- [ ] **Step 6: Playwright regression**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts`
Expected: same pass/fail pattern as baseline. Any NEW failure = revert and investigate.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Move ExtractionReview to shared lcopilot components"
```

---

## Task 2: Extract LcIntakeCard

**Files:**
- Create: `apps/web/src/components/lcopilot/LcIntakeCard.tsx`
- Modify: `apps/web/src/pages/ExportLCUpload.tsx` (extract inline JSX + LcIntakeState type)

- [ ] **Step 1: Locate the LC intake card in ExportLCUpload.tsx**

Run:
```
grep -n "LCIntakeState\|LcIntakeState\|LC intake\|lcIntakeCard\|LcIntakeCard" apps/web/src/pages/ExportLCUpload.tsx | head -10
```
Expected: several line numbers. Read lines around `LCIntakeState` interface (around line 85-100 per audit).

- [ ] **Step 2: Read the full intake card JSX block**

Read lines ~85-250 of `ExportLCUpload.tsx` to identify the self-contained card component + its props + the `LCIntakeState` interface.

- [ ] **Step 3: Create the new shared component file**

Create `apps/web/src/components/lcopilot/LcIntakeCard.tsx` with the following structure (copy the JSX from ExportLCUpload.tsx verbatim, extract only what belongs to the card):

```typescript
// Content mirrors the inline JSX from ExportLCUpload.tsx — see Step 2.
// Move the LCIntakeState interface + the card JSX + any helper functions
// that are only used by this card (detection basis formatter, etc.)
// Export the component and the type.

export interface LcIntakeState {
  // exact fields from ExportLCUpload.tsx LCIntakeState interface
}

export function LcIntakeCard(props: { state: LcIntakeState; /* other props used by the card */ }) {
  // exact JSX from ExportLCUpload.tsx
  return (/* ... */);
}
```

Preserve exact class names, icon choices, copy strings. This is a move, not a rewrite.

- [ ] **Step 4: Replace the inline JSX in ExportLCUpload.tsx with the component**

In `ExportLCUpload.tsx`:
- Add import: `import { LcIntakeCard, type LcIntakeState } from "@/components/lcopilot/LcIntakeCard";`
- Remove the `LCIntakeState` interface definition
- Replace the inline intake card JSX with `<LcIntakeCard state={...} {...otherProps} />`

- [ ] **Step 5: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS.

- [ ] **Step 6: Playwright regression**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts`
Expected: same pass/fail pattern as baseline.

- [ ] **Step 7: Visual smoke — intake card still renders identically**

Manually (or via MCP browser): load the exporter upload page, drop an LC. Verify the intake card UI is pixel-identical to before (same icons, same copy, same layout).

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Extract LcIntakeCard to shared lcopilot components"
```

---

## Task 3: Extract useExtractionPayloadStore (sessionStorage helper)

**Files:**
- Create: `apps/web/src/hooks/use-extraction-payload-store.ts`
- Modify: `apps/web/src/pages/ExportLCUpload.tsx` (remove inline storage logic, import hook)

- [ ] **Step 1: Locate sessionStorage logic in ExportLCUpload.tsx**

Run:
```
grep -n "sessionStorage\|EXTRACTION_STORAGE_KEY\|extractionPayload" apps/web/src/pages/ExportLCUpload.tsx | head -20
```
Expected: multiple lines around 605-623 per audit. Read that region.

- [ ] **Step 2: Write a failing test**

Create `apps/web/src/hooks/__tests__/use-extraction-payload-store.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useExtractionPayloadStore } from "../use-extraction-payload-store";

describe("useExtractionPayloadStore", () => {
  beforeEach(() => sessionStorage.clear());

  it("persists payload to sessionStorage under the canonical key", () => {
    const { result } = renderHook(() => useExtractionPayloadStore());
    act(() => result.current.save({ jobId: "job-123", documents: [] }));
    const raw = sessionStorage.getItem("lcopilot:extraction-payload");
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw!)).toMatchObject({ jobId: "job-123" });
  });

  it("restores payload on mount if present", () => {
    sessionStorage.setItem(
      "lcopilot:extraction-payload",
      JSON.stringify({ jobId: "job-456", documents: [] })
    );
    const { result } = renderHook(() => useExtractionPayloadStore());
    expect(result.current.payload?.jobId).toBe("job-456");
  });

  it("clear() removes the storage key", () => {
    const { result } = renderHook(() => useExtractionPayloadStore());
    act(() => result.current.save({ jobId: "job-789", documents: [] }));
    act(() => result.current.clear());
    expect(sessionStorage.getItem("lcopilot:extraction-payload")).toBeNull();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/web && npm run test -- use-extraction-payload-store`
Expected: FAIL ("Cannot find module …").

- [ ] **Step 4: Implement the hook**

Create `apps/web/src/hooks/use-extraction-payload-store.ts`:

```typescript
import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "lcopilot:extraction-payload";

export interface ExtractionPayload {
  jobId: string;
  documents: unknown[];
  [key: string]: unknown;
}

export function useExtractionPayloadStore() {
  const [payload, setPayload] = useState<ExtractionPayload | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as ExtractionPayload) : null;
    } catch {
      return null;
    }
  });

  const save = useCallback((next: ExtractionPayload) => {
    setPayload(next);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }, []);

  const clear = useCallback(() => {
    setPayload(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY) return;
      setPayload(e.newValue ? (JSON.parse(e.newValue) as ExtractionPayload) : null);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { payload, save, clear };
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/web && npm run test -- use-extraction-payload-store`
Expected: 3/3 PASS.

- [ ] **Step 6: Replace inline logic in ExportLCUpload.tsx**

Read `apps/web/src/pages/ExportLCUpload.tsx` around the sessionStorage lines. Replace the inline `sessionStorage.getItem(...)`, `sessionStorage.setItem(...)` calls, and the local storage-key constant with the new hook:

```typescript
const { payload: restoredPayload, save: savePayload, clear: clearPayload } = useExtractionPayloadStore();
```

Update all existing call sites to use `savePayload(...)` / `clearPayload()` / `restoredPayload`. If the key name was different from `"lcopilot:extraction-payload"`, update the hook to match (don't silently change keys — users with saved state would lose it).

- [ ] **Step 7: Type-check + unit tests + Playwright regression**

Run:
```
cd apps/web && npm run type-check && npm run test && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts
```
Expected: all PASS.

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Extract sessionStorage persistence into use-extraction-payload-store hook"
```

---

## Task 4: Extract resultsMapper

**Files:**
- Move: `apps/web/src/lib/exporter/resultsMapper.ts` → `apps/web/src/lib/lcopilot/resultsMapper.ts`
- Modify: all importers

- [ ] **Step 1: Find all referrers**

Run:
```
cd apps/web/src && grep -rln "lib/exporter/resultsMapper\|exporter/resultsMapper" . --include="*.ts" --include="*.tsx"
```

- [ ] **Step 2: Ensure target directory exists**

Run: `mkdir -p apps/web/src/lib/lcopilot`

- [ ] **Step 3: Move the file**

Run:
```
git mv apps/web/src/lib/exporter/resultsMapper.ts apps/web/src/lib/lcopilot/resultsMapper.ts
```

- [ ] **Step 4: Update every referrer**

For each file in Step 1:
```
from "@/lib/exporter/resultsMapper"   →   from "@/lib/lcopilot/resultsMapper"
from "../lib/exporter/resultsMapper"  →   from "../lib/lcopilot/resultsMapper"
from "../../lib/exporter/resultsMapper" → from "../../lib/lcopilot/resultsMapper"
```

- [ ] **Step 5: Verify companion tests move with it**

Check `apps/web/src/lib/exporter/__tests__/` for any `resultsMapper.test.ts`. If present, git-mv it to `apps/web/src/lib/lcopilot/__tests__/resultsMapper.test.ts` and update imports inside.

- [ ] **Step 6: Type-check + unit tests + Playwright regression**

Run:
```
cd apps/web && npm run type-check && npm run test && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Move resultsMapper to shared lcopilot lib"
```

---

## Task 5: Extract results-tab shell

**Files:**
- Move: `apps/web/src/pages/exporter/results/tabs/VerdictTab.tsx` → `apps/web/src/components/lcopilot/results/tabs/VerdictTab.tsx`
- Move: `apps/web/src/pages/exporter/results/tabs/DocumentsTab.tsx` → `apps/web/src/components/lcopilot/results/tabs/DocumentsTab.tsx`
- Move: `apps/web/src/pages/exporter/results/tabs/FindingsTab.tsx` → `apps/web/src/components/lcopilot/results/tabs/FindingsTab.tsx`
- Move: `apps/web/src/pages/exporter/results/tabs/HistoryTab.tsx` → `apps/web/src/components/lcopilot/results/tabs/HistoryTab.tsx`
- Move: any `index.ts` barrel if present
- Modify: all importers

- [ ] **Step 1: Verify all 4 tab files exist at the expected path**

Run: `ls apps/web/src/pages/exporter/results/tabs/`
Expected: 4 `.tsx` files (may have additional helpers — list them all).

- [ ] **Step 2: Find all referrers**

Run:
```
cd apps/web/src && grep -rln "pages/exporter/results/tabs\|exporter/results/tabs" . --include="*.ts" --include="*.tsx"
```

- [ ] **Step 3: Create target directory**

Run: `mkdir -p apps/web/src/components/lcopilot/results/tabs`

- [ ] **Step 4: Move each file (preserve sibling helpers in the same dir)**

Run for each file:
```
git mv apps/web/src/pages/exporter/results/tabs/VerdictTab.tsx apps/web/src/components/lcopilot/results/tabs/VerdictTab.tsx
git mv apps/web/src/pages/exporter/results/tabs/DocumentsTab.tsx apps/web/src/components/lcopilot/results/tabs/DocumentsTab.tsx
git mv apps/web/src/pages/exporter/results/tabs/FindingsTab.tsx apps/web/src/components/lcopilot/results/tabs/FindingsTab.tsx
git mv apps/web/src/pages/exporter/results/tabs/HistoryTab.tsx apps/web/src/components/lcopilot/results/tabs/HistoryTab.tsx
```

Also move any sibling helpers (barrel `index.ts`, `types.ts`, co-located helpers) in the same git-mv batch.

- [ ] **Step 5: Update every referrer**

For each file in Step 2:
```
from ".../pages/exporter/results/tabs/VerdictTab"   →   from "@/components/lcopilot/results/tabs/VerdictTab"
(same for DocumentsTab, FindingsTab, HistoryTab)
```

- [ ] **Step 6: Add actionSlot prop to VerdictTab (Phase 2 dependency)**

Open `apps/web/src/components/lcopilot/results/tabs/VerdictTab.tsx`. Add a new optional prop to the props interface:

```typescript
export interface VerdictTabProps {
  // ... existing props
  actionSlot?: React.ReactNode;
}
```

Inside the component, render `{actionSlot}` in the action-rail location (wherever the current "submit to bank" etc. buttons live). If `actionSlot` is undefined, render the current exporter action buttons as the default — preserves exporter behavior.

- [ ] **Step 7: Update exporter results page to pass actionSlot explicitly (optional but cleaner)**

In the file that renders `<VerdictTab />` for exporter (likely `ExporterResultsV2.tsx` or `ExporterResults.tsx`), explicitly pass the current exporter action buttons as `actionSlot={<ExporterActions ... />}`. This is optional — default-fallback also works. If unclear, leave as default.

- [ ] **Step 8: Type-check + unit tests + Playwright regression**

Run:
```
cd apps/web && npm run type-check && npm run test && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts
```
Expected: all PASS.

- [ ] **Step 9: Commit**

```
git add -A
git commit -m "Move results tab shell to shared lcopilot components + add actionSlot prop"
```

---

## Task 6: Extract PreparationGuide

**Files:**
- Move: `apps/web/src/components/exporter/PreparationGuide.tsx` (or wherever it lives) → `apps/web/src/components/lcopilot/PreparationGuide.tsx`
- Modify: all importers

- [ ] **Step 1: Locate PreparationGuide**

Run:
```
cd apps/web/src && grep -rln "PreparationGuide" . --include="*.ts" --include="*.tsx"
```
Expected: find the file that defines the component (exporting `PreparationGuide`) and all importers.

- [ ] **Step 2: Move the file**

Run:
```
git mv <source-path>/PreparationGuide.tsx apps/web/src/components/lcopilot/PreparationGuide.tsx
```
(replace `<source-path>` with actual path from Step 1)

- [ ] **Step 3: Update every referrer's import path**

Replace old path → `@/components/lcopilot/PreparationGuide` everywhere.

- [ ] **Step 4: Type-check + unit tests + Playwright regression**

Run:
```
cd apps/web && npm run type-check && npm run test && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add -A
git commit -m "Move PreparationGuide to shared lcopilot components"
```

---

## Task 7: Create (or extract) ReviewsTable

**Files:**
- Create or Move: `apps/web/src/components/lcopilot/ReviewsTable.tsx`

- [ ] **Step 1: Check if a reviews-list component already exists**

Run:
```
cd apps/web/src && grep -rln "ReviewsTable\|RecentValidationsCard\|sessionsToHistory" . --include="*.ts" --include="*.tsx" | head -10
```

- [ ] **Step 2a: If `RecentValidationsCard` exists and is reusable — extract it**

If a reusable list component already exists (e.g., `RecentValidationsCard`), `git mv` it to `apps/web/src/components/lcopilot/ReviewsTable.tsx`, rename the component to `ReviewsTable`, and update all referrers. Skip to Step 3.

- [ ] **Step 2b: If nothing suitable exists — write a failing test for a new one**

Create `apps/web/src/components/lcopilot/__tests__/ReviewsTable.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReviewsTable } from "../ReviewsTable";

describe("ReviewsTable", () => {
  it("renders one row per session", () => {
    const sessions = [
      { id: "s1", lcNumber: "LC-001", createdAt: "2026-04-21T00:00:00Z", verdict: "pass", workflowType: "exporter_presentation" },
      { id: "s2", lcNumber: "LC-002", createdAt: "2026-04-20T00:00:00Z", verdict: "review", workflowType: "importer_draft_lc" },
    ];
    render(<ReviewsTable sessions={sessions} />);
    expect(screen.getByText("LC-001")).toBeInTheDocument();
    expect(screen.getByText("LC-002")).toBeInTheDocument();
  });

  it("renders a type badge per row based on workflowType", () => {
    const sessions = [
      { id: "s1", lcNumber: "LC-A", createdAt: "2026-04-21T00:00:00Z", verdict: "pass", workflowType: "importer_draft_lc" as const },
    ];
    render(<ReviewsTable sessions={sessions} />);
    expect(screen.getByText(/draft lc/i)).toBeInTheDocument();
  });

  it("renders empty state when no sessions", () => {
    render(<ReviewsTable sessions={[]} />);
    expect(screen.getByText(/no (recent )?(activity|reviews)/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2c: Run test to verify it fails**

Run: `cd apps/web && npm run test -- ReviewsTable`
Expected: FAIL (module not found).

- [ ] **Step 2d: Implement ReviewsTable**

Create `apps/web/src/components/lcopilot/ReviewsTable.tsx`:

```typescript
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";

export interface ReviewsTableSession {
  id: string;
  lcNumber: string;
  createdAt: string;
  verdict: "pass" | "review" | "reject" | string;
  workflowType: "exporter_presentation" | "importer_draft_lc" | "importer_supplier_docs";
  resultsHref?: string;
}

export interface ReviewsTableProps {
  sessions: ReviewsTableSession[];
  emptyMessage?: string;
}

const TYPE_LABEL: Record<ReviewsTableSession["workflowType"], string> = {
  exporter_presentation: "PRESENTATION",
  importer_draft_lc: "DRAFT LC",
  importer_supplier_docs: "SHIPMENT",
};

export function ReviewsTable({ sessions, emptyMessage = "No recent activity" }: ReviewsTableProps) {
  if (sessions.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">{emptyMessage}</p>;
  }
  return (
    <ul className="divide-y">
      {sessions.map((s) => (
        <li key={s.id} className="flex items-center gap-3 py-2">
          <Badge variant="outline">{TYPE_LABEL[s.workflowType] ?? s.workflowType}</Badge>
          <span className="font-medium">{s.lcNumber}</span>
          <span className="ml-auto text-xs text-muted-foreground">
            {new Date(s.createdAt).toLocaleDateString()}
          </span>
          {s.resultsHref && (
            <Link to={s.resultsHref} className="text-sm text-primary hover:underline">
              View →
            </Link>
          )}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2e: Run test to verify it passes**

Run: `cd apps/web && npm run test -- ReviewsTable`
Expected: 3/3 PASS.

- [ ] **Step 3: Type-check + Playwright regression**

Run:
```
cd apps/web && npm run type-check && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts
```
Expected: PASS.

- [ ] **Step 4: Commit**

If Step 2a path (extracted existing):
```
git add -A
git commit -m "Extract ReviewsTable to shared lcopilot components"
```

If Step 2b path (built fresh):
```
git add -A
git commit -m "Add ReviewsTable shared component for dashboard recent activity"
```

---

## Task 8: Confirm parseExtractionResponse lives in shared home

**Files:**
- Verify: `apps/web/src/hooks/use-lcopilot.ts` (already shared — no move needed)

- [ ] **Step 1: Confirm parseExtractionResponse is exported**

Run:
```
grep -n "parseExtractionResponse" apps/web/src/hooks/use-lcopilot.ts
```
Expected: export statement found.

- [ ] **Step 2: Add explicit re-export for discoverability (optional)**

Create `apps/web/src/lib/lcopilot/zod.ts`:

```typescript
export { parseExtractionResponse } from "@/hooks/use-lcopilot";
export type { ValidationError } from "@/hooks/use-lcopilot";
```

This is cosmetic — the hook file already works. Skip if it feels like over-engineering.

- [ ] **Step 3: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS.

- [ ] **Step 4: Commit (only if Step 2 was done)**

```
git add -A
git commit -m "Re-export parseExtractionResponse from lib/lcopilot/zod for discoverability"
```

---

## Task 9: Final Phase 1 verification

**Files:**
- Verify: all

- [ ] **Step 1: Full test sweep**

Run:
```
cd apps/web && npm run type-check && npm run lint && npm run test
```
Expected: all PASS.

- [ ] **Step 2: Full Playwright regression (exporter + smoke)**

Run:
```
cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts tests/e2e/smoke.spec.ts
```
Expected: all PASS.

- [ ] **Step 3: Diff captured baseline**

Run:
```
cd apps/web && npx playwright test tests/e2e/lcopilot/exporter-validation.spec.ts --reporter=json > /tmp/phase1-final.json
diff /tmp/phase1-baseline.json /tmp/phase1-final.json
```
Expected: identical pass/fail pattern (test-result metadata like durations/timestamps may differ; status values must not).

- [ ] **Step 4: Manual exporter smoke (5 min)**

Start dev server:
```
cd apps/web && npm run dev
```
Log in, upload IDEAL SAMPLE LC, run extract → review → validate → results. Verify:
- Intake card renders identically
- Extraction review renders identically
- All 4 result tabs render identically
- No console errors

- [ ] **Step 5: No commit — this is pure verification. Exit Phase 1.**

---

## Phase 1 Exit Criteria

- [ ] All 7 pieces extracted to `apps/web/src/components/lcopilot/` (or `lib/lcopilot/`)
- [ ] Zero imports remaining from old exporter paths for those pieces
- [ ] Type-check, lint, unit tests, exporter Playwright — all green
- [ ] Manual exporter golden path verified identical
- [ ] Git log shows one commit per piece for clean bisect

Phase 1 complete. Proceed to Phase 2 plan.
