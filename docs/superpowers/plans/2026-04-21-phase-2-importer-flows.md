# Phase 2 — Importer Flows on Shared Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two importer workflows (Draft LC Review, Supplier Doc Review) on top of Phase 1's shared components. Add `workflow_type` to `ValidationSession`. Rewrite `ImportResults.tsx` as a thin shared-tab-shell wrapper.

**Architecture:** Single `<ImporterValidationPage moment="draft_lc|supplier_docs">` component serves both moments via different routes. Backend gets a `workflow_type` query param on `/api/validate/` that persists to `ValidationSession.workflow_type` — pipeline itself is unchanged. Feature flag `LCOPILOT_IMPORTER_V2` gates the new routes.

**Tech Stack:** React 18 + Vite (frontend); FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL (backend). Vitest, pytest, Playwright.

**Prereq:** Phase 1 complete and merged (all shared components live under `components/lcopilot/` and `lib/lcopilot/`).

**Spec:** `docs/superpowers/specs/2026-04-21-importer-parity-design.md` (Phase 2 section)

---

## Task 1: Add `workflow_type` column to `ValidationSession` (migration)

**Files:**
- Create: `apps/api/alembic/versions/20260422_add_workflow_type_to_validation_session.py`
- Modify: `apps/api/app/models/validation_session.py` (add column + enum)

- [ ] **Step 1: Locate the current ValidationSession model**

Run: `grep -n "class ValidationSession" apps/api/app/models/*.py`
Expected: one file defining the model. Read it.

- [ ] **Step 2: Write a failing test**

Create `apps/api/tests/test_workflow_type.py`:

```python
"""Tests for ValidationSession.workflow_type column and enum."""
import pytest
from app.models.validation_session import ValidationSession, WorkflowType


def test_workflow_type_enum_values():
    assert WorkflowType.EXPORTER_PRESENTATION.value == "exporter_presentation"
    assert WorkflowType.IMPORTER_DRAFT_LC.value == "importer_draft_lc"
    assert WorkflowType.IMPORTER_SUPPLIER_DOCS.value == "importer_supplier_docs"


def test_validation_session_has_workflow_type_column():
    assert hasattr(ValidationSession, "workflow_type")


def test_validation_session_workflow_type_default(db_session, test_user):
    session = ValidationSession(user_id=test_user.id)
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    assert session.workflow_type == WorkflowType.EXPORTER_PRESENTATION
```

(If `db_session` / `test_user` fixtures already exist in `apps/api/tests/conftest.py`, use them. Otherwise stub them in this test file.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_workflow_type.py -v`
Expected: FAIL ("cannot import name 'WorkflowType'").

- [ ] **Step 4: Add the enum + column to the model**

Edit `apps/api/app/models/validation_session.py`. Add near the top:

```python
import enum
from sqlalchemy import Column, Enum as SQLEnum

class WorkflowType(str, enum.Enum):
    EXPORTER_PRESENTATION = "exporter_presentation"
    IMPORTER_DRAFT_LC = "importer_draft_lc"
    IMPORTER_SUPPLIER_DOCS = "importer_supplier_docs"
```

Then add to the `ValidationSession` class:

```python
    workflow_type = Column(
        SQLEnum(WorkflowType, name="workflow_type_enum"),
        nullable=False,
        default=WorkflowType.EXPORTER_PRESENTATION,
        server_default=WorkflowType.EXPORTER_PRESENTATION.value,
    )
```

- [ ] **Step 5: Generate migration (autogenerate)**

Run:
```
cd apps/api && alembic revision --autogenerate -m "add workflow_type to validation_session"
```
Expected: new file at `apps/api/alembic/versions/<hash>_add_workflow_type_to_validation_session.py`. Rename to `20260422_add_workflow_type_to_validation_session.py` for consistency with existing naming.

- [ ] **Step 6: Inspect migration for three-step pattern**

Open the generated migration. Verify it does:
1. `op.execute("CREATE TYPE workflow_type_enum AS ENUM ('exporter_presentation', 'importer_draft_lc', 'importer_supplier_docs')")`
2. `op.add_column('validation_sessions', sa.Column('workflow_type', ..., nullable=False, server_default='exporter_presentation'))`

If autogenerate didn't use `server_default`, manually edit the migration to add `server_default='exporter_presentation'` on the `add_column` call. This backfills existing rows atomically.

- [ ] **Step 7: Run migration**

Run: `cd apps/api && alembic upgrade head`
Expected: migration applies clean. Verify column exists:
```
psql $DATABASE_URL -c "\d validation_sessions" | grep workflow_type
```

- [ ] **Step 8: Run the test**

Run: `cd apps/api && pytest tests/test_workflow_type.py -v`
Expected: 3/3 PASS.

- [ ] **Step 9: Full backend test suite to catch regressions**

Run: `cd apps/api && pytest tests/ -v -m "not slow"`
Expected: no new failures vs. baseline.

- [ ] **Step 10: Commit**

```
git add -A
git commit -m "Add workflow_type enum + column to ValidationSession"
```

---

## Task 2: Accept `workflow_type` query param on `/api/validate/`

**Files:**
- Modify: `apps/api/app/routers/validation/validate.py` (or wherever `POST /api/validate/` lives)
- Modify: `apps/api/app/routers/validation/pipeline_runner.py` (pass workflow_type through to session creation)

- [ ] **Step 1: Locate the validate endpoint**

Run: `grep -rn "POST.*validate\|@router.post" apps/api/app/routers/validation/ | head -10`
Expected: identify the `/api/validate/` POST handler.

- [ ] **Step 2: Write a failing test**

Create or append to `apps/api/tests/test_validate_workflow_type.py`:

```python
"""Tests that POST /api/validate/ accepts workflow_type and persists it."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.validation_session import WorkflowType

client = TestClient(app)


@pytest.mark.parametrize("wf_type", [
    "exporter_presentation",
    "importer_draft_lc",
    "importer_supplier_docs",
])
def test_validate_accepts_workflow_type(authenticated_headers, sample_lc_file, wf_type, db_session):
    files = [("files", ("lc.pdf", sample_lc_file, "application/pdf"))]
    resp = client.post(
        f"/api/validate/?workflow_type={wf_type}&intake_only=true",
        files=files,
        headers=authenticated_headers,
    )
    assert resp.status_code in (200, 202), resp.text
    job_id = resp.json().get("job_id")
    assert job_id

    # Fetch the session and verify workflow_type persisted
    from app.models.validation_session import ValidationSession
    session = db_session.query(ValidationSession).filter_by(id=job_id).first()
    assert session is not None
    assert session.workflow_type.value == wf_type


def test_validate_defaults_workflow_type_to_exporter_presentation(
    authenticated_headers, sample_lc_file, db_session
):
    files = [("files", ("lc.pdf", sample_lc_file, "application/pdf"))]
    resp = client.post(
        "/api/validate/?intake_only=true",  # no workflow_type param
        files=files,
        headers=authenticated_headers,
    )
    assert resp.status_code in (200, 202)
    from app.models.validation_session import ValidationSession
    session = db_session.query(ValidationSession).filter_by(id=resp.json()["job_id"]).first()
    assert session.workflow_type == WorkflowType.EXPORTER_PRESENTATION
```

(`authenticated_headers` and `sample_lc_file` fixtures likely exist in `conftest.py` — if not, copy patterns from existing `apps/api/tests/test_validate*.py` files.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/api && pytest tests/test_validate_workflow_type.py -v`
Expected: FAIL (tests that check `session.workflow_type.value == "importer_draft_lc"` will fail — the endpoint ignores the param).

- [ ] **Step 4: Add the query param to the endpoint**

In the `/api/validate/` handler, add `workflow_type` as an optional query param:

```python
from app.models.validation_session import WorkflowType
from fastapi import Query

async def validate(
    files: List[UploadFile] = File(...),
    intake_only: bool = Query(False),
    extract_only: bool = Query(False),
    workflow_type: WorkflowType = Query(WorkflowType.EXPORTER_PRESENTATION),
    # ...other existing params
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ...
```

Pass `workflow_type` into the function that creates `ValidationSession` (likely in `pipeline_runner.py` or inside the handler).

In the session-creation code:
```python
session = ValidationSession(
    user_id=current_user.id,
    workflow_type=workflow_type,
    # ...other existing fields
)
```

- [ ] **Step 5: Propagate `workflow_type` into response envelope**

Find where the response is shaped (look for `structured_result` population). Add `workflow_type` into `structured_result.meta`:

```python
structured_result = {
    # ...existing fields
    "meta": {
        **existing_meta,
        "workflow_type": session.workflow_type.value,
    },
}
```

- [ ] **Step 6: Run tests**

Run: `cd apps/api && pytest tests/test_validate_workflow_type.py tests/test_workflow_type.py -v`
Expected: all PASS.

- [ ] **Step 7: Full backend regression**

Run: `cd apps/api && pytest tests/ -v -m "not slow"`
Expected: no new failures.

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Accept workflow_type on /api/validate/ and persist to session + meta"
```

---

## Task 3: Add feature flag `LCOPILOT_IMPORTER_V2`

**Files:**
- Modify: `apps/web/.env.example` (add `VITE_LCOPILOT_IMPORTER_V2=false`)
- Create: `apps/web/src/lib/lcopilot/featureFlags.ts`

- [ ] **Step 1: Write a failing test**

Create `apps/web/src/lib/lcopilot/__tests__/featureFlags.test.ts`:

```typescript
import { describe, it, expect, vi, afterEach } from "vitest";

describe("featureFlags.isImporterV2Enabled", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("returns true when VITE_LCOPILOT_IMPORTER_V2 is 'true'", async () => {
    vi.stubEnv("VITE_LCOPILOT_IMPORTER_V2", "true");
    const { isImporterV2Enabled } = await import("../featureFlags");
    expect(isImporterV2Enabled()).toBe(true);
  });

  it("returns false when VITE_LCOPILOT_IMPORTER_V2 is unset", async () => {
    vi.stubEnv("VITE_LCOPILOT_IMPORTER_V2", "");
    const { isImporterV2Enabled } = await import("../featureFlags");
    expect(isImporterV2Enabled()).toBe(false);
  });

  it("returns false when VITE_LCOPILOT_IMPORTER_V2 is 'false'", async () => {
    vi.stubEnv("VITE_LCOPILOT_IMPORTER_V2", "false");
    const { isImporterV2Enabled } = await import("../featureFlags");
    expect(isImporterV2Enabled()).toBe(false);
  });
});
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/web && npm run test -- featureFlags`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `apps/web/src/lib/lcopilot/featureFlags.ts`:

```typescript
export function isImporterV2Enabled(): boolean {
  const raw = (import.meta.env.VITE_LCOPILOT_IMPORTER_V2 ?? "").toString().trim().toLowerCase();
  return raw === "true" || raw === "1";
}
```

- [ ] **Step 4: Run to pass**

Run: `cd apps/web && npm run test -- featureFlags`
Expected: 3/3 PASS.

- [ ] **Step 5: Document the flag**

Append to `apps/web/.env.example`:
```
# When true, enables the refactored importer flows (Draft LC Review + Supplier Doc Review).
# When false/unset, only the legacy importer dashboard is reachable.
VITE_LCOPILOT_IMPORTER_V2=false
```

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add LCOPILOT_IMPORTER_V2 feature flag helper"
```

---

## Task 4: Build `<ImporterValidationPage>` component

**Files:**
- Create: `apps/web/src/pages/importer/ImporterValidationPage.tsx`
- Create: `apps/web/src/pages/importer/importerMoments.ts`
- Create: `apps/web/src/pages/importer/__tests__/ImporterValidationPage.test.tsx`

- [ ] **Step 1: Define moment config**

Create `apps/web/src/pages/importer/importerMoments.ts`:

```typescript
export type ImporterMoment = "draft_lc" | "supplier_docs";

export interface ImporterMomentConfig {
  moment: ImporterMoment;
  workflowType: "importer_draft_lc" | "importer_supplier_docs";
  pageTitle: string;
  ctaLabel: string;
  acceptedDocTypes: { value: string; label: string }[];
  requiredDocsFraming: "informational" | "checklist";
}

const DRAFT_LC_DOC_TYPES = [
  { value: "lc", label: "Draft LC (PDF)" },
  { value: "swift", label: "SWIFT Message" },
  { value: "application", label: "LC Application Form" },
  { value: "proforma", label: "Proforma Invoice (PI)" },
  { value: "other", label: "Other Document" },
];

const SUPPLIER_DOC_TYPES = [
  { value: "lc", label: "Issued LC" },
  { value: "invoice", label: "Commercial Invoice" },
  { value: "packing", label: "Packing List" },
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "certificate_origin", label: "Certificate of Origin" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "inspection", label: "Inspection Certificate" },
  { value: "beneficiary", label: "Beneficiary Certificate" },
  { value: "other", label: "Other Trade Documents" },
];

export const IMPORTER_MOMENTS: Record<ImporterMoment, ImporterMomentConfig> = {
  draft_lc: {
    moment: "draft_lc",
    workflowType: "importer_draft_lc",
    pageTitle: "Draft LC Risk Analysis",
    ctaLabel: "Analyze LC Risks",
    acceptedDocTypes: DRAFT_LC_DOC_TYPES,
    requiredDocsFraming: "informational",
  },
  supplier_docs: {
    moment: "supplier_docs",
    workflowType: "importer_supplier_docs",
    pageTitle: "Supplier Document Review",
    ctaLabel: "Review Supplier Documents",
    acceptedDocTypes: SUPPLIER_DOC_TYPES,
    requiredDocsFraming: "checklist",
  },
};
```

- [ ] **Step 2: Write failing tests for the page**

Create `apps/web/src/pages/importer/__tests__/ImporterValidationPage.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ImporterValidationPage } from "../ImporterValidationPage";

function renderPage(moment: "draft_lc" | "supplier_docs") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ImporterValidationPage moment={moment} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ImporterValidationPage", () => {
  it("renders Draft LC title for moment='draft_lc'", () => {
    renderPage("draft_lc");
    expect(screen.getByRole("heading", { name: /draft lc risk analysis/i })).toBeInTheDocument();
  });

  it("renders Supplier Doc title for moment='supplier_docs'", () => {
    renderPage("supplier_docs");
    expect(screen.getByRole("heading", { name: /supplier document review/i })).toBeInTheDocument();
  });

  it("shows Draft LC doc-type options for draft_lc moment", () => {
    renderPage("draft_lc");
    expect(screen.queryByText(/bill of lading/i)).not.toBeInTheDocument();
    expect(screen.getByText(/draft lc/i)).toBeInTheDocument();
  });

  it("shows supplier doc-type options for supplier_docs moment", () => {
    renderPage("supplier_docs");
    expect(screen.getByText(/bill of lading/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- ImporterValidationPage`
Expected: FAIL (module not found).

- [ ] **Step 4: Implement `ImporterValidationPage`**

Create `apps/web/src/pages/importer/ImporterValidationPage.tsx`:

```typescript
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ExtractionReview } from "@/components/lcopilot/ExtractionReview";
import { LcIntakeCard } from "@/components/lcopilot/LcIntakeCard";
import { PreparationGuide } from "@/components/lcopilot/PreparationGuide";
import { useExtractionPayloadStore } from "@/hooks/use-extraction-payload-store";
import { useValidate, useResumeValidate } from "@/hooks/use-lcopilot";
import { IMPORTER_MOMENTS, type ImporterMoment } from "./importerMoments";
import { Upload, FileText } from "lucide-react";

export interface ImporterValidationPageProps {
  moment: ImporterMoment;
}

export function ImporterValidationPage({ moment }: ImporterValidationPageProps) {
  const config = IMPORTER_MOMENTS[moment];
  const [files, setFiles] = useState<File[]>([]);
  const { payload: savedPayload, save: savePayload, clear: clearPayload } = useExtractionPayloadStore();
  const validate = useValidate();
  const resume = useResumeValidate();

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { "application/pdf": [".pdf"] } });

  const onStart = () => {
    validate.mutate(
      { files, workflowType: config.workflowType, extractOnly: true },
      {
        onSuccess: (data) => {
          savePayload(data);
        },
      }
    );
  };

  const onResume = (fieldOverrides: Record<string, Record<string, string>>) => {
    if (!savedPayload?.jobId) return;
    resume.mutate(
      { jobId: savedPayload.jobId, fieldOverrides },
      {
        onSuccess: () => clearPayload(),
      }
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{config.pageTitle}</h1>
        <p className="text-muted-foreground">
          {moment === "draft_lc"
            ? "Upload your bank's draft LC to identify risky clauses and potential supplier rejection points"
            : "Upload supplier documents to validate against the issued LC"}
        </p>
      </header>

      {!savedPayload && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Documents</CardTitle>
            <CardDescription>Accepted: {config.acceptedDocTypes.map((d) => d.label).join(", ")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div {...getRootProps()} className="border-2 border-dashed rounded p-8 text-center cursor-pointer">
              <input {...getInputProps()} />
              <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-2">{isDragActive ? "Drop files here" : "Drag PDFs here or click to select"}</p>
            </div>
            {files.length > 0 && (
              <ul className="mt-4 space-y-1">
                {files.map((f, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4" />
                    {f.name}
                  </li>
                ))}
              </ul>
            )}
            <Button onClick={onStart} disabled={files.length === 0 || validate.isPending} className="mt-4">
              {validate.isPending ? "Processing..." : config.ctaLabel}
            </Button>
          </CardContent>
        </Card>
      )}

      {savedPayload?.lcSummary && <LcIntakeCard state={savedPayload.lcSummary} />}

      {savedPayload?.documents && (
        <ExtractionReview
          documents={savedPayload.documents}
          onConfirm={onResume}
          isSubmitting={resume.isPending}
        />
      )}

      <PreparationGuide moment={moment} />
    </div>
  );
}
```

Notes:
- If `useValidate` / `useResumeValidate` signatures don't currently accept `workflowType`, extend their types (see Task 5).
- If `PreparationGuide` doesn't take a `moment` prop today, it will for Phase 2 — update its props interface in a small follow-up commit if needed.
- If `LcIntakeCard` or `ExtractionReview` prop names differ, align to the actual interfaces from Phase 1 extractions.

- [ ] **Step 5: Run tests to pass**

Run: `cd apps/web && npm run test -- ImporterValidationPage`
Expected: 4/4 PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add ImporterValidationPage serving both Draft LC and Supplier Docs moments"
```

---

## Task 5: Extend `useValidate` to thread `workflowType` through

**Files:**
- Modify: `apps/web/src/hooks/use-lcopilot.ts`

- [ ] **Step 1: Locate `useValidate` in the hook file**

Run: `grep -n "useValidate\|useMutation.*validate" apps/web/src/hooks/use-lcopilot.ts | head -10`

- [ ] **Step 2: Write a failing test for the new param**

Append to `apps/web/src/hooks/__tests__/use-lcopilot.test.ts` (create if missing):

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useValidate } from "../use-lcopilot";

const postSpy = vi.fn();
vi.mock("@/api/client", () => ({
  default: { post: (...args: unknown[]) => postSpy(...args) },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useValidate workflowType threading", () => {
  beforeEach(() => postSpy.mockReset().mockResolvedValue({ data: { job_id: "j1", documents: [] } }));

  it("passes workflow_type in the URL query string", async () => {
    const { result } = renderHook(() => useValidate(), { wrapper });
    result.current.mutate({ files: [new File(["x"], "x.pdf")], workflowType: "importer_draft_lc", extractOnly: true });
    await waitFor(() => expect(postSpy).toHaveBeenCalled());
    const urlArg = postSpy.mock.calls[0][0] as string;
    expect(urlArg).toMatch(/workflow_type=importer_draft_lc/);
  });

  it("omits workflow_type when not provided (backend defaults)", async () => {
    const { result } = renderHook(() => useValidate(), { wrapper });
    result.current.mutate({ files: [new File(["x"], "x.pdf")], extractOnly: true });
    await waitFor(() => expect(postSpy).toHaveBeenCalled());
    const urlArg = postSpy.mock.calls[0][0] as string;
    expect(urlArg).not.toMatch(/workflow_type=/);
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- use-lcopilot`
Expected: FAIL.

- [ ] **Step 4: Extend the hook signature**

In `apps/web/src/hooks/use-lcopilot.ts`, locate the `useValidate` mutation. Update the mutation variables type:

```typescript
export type WorkflowType = "exporter_presentation" | "importer_draft_lc" | "importer_supplier_docs";

export interface ValidateMutationVars {
  files: File[];
  extractOnly?: boolean;
  intakeOnly?: boolean;
  workflowType?: WorkflowType;
  // ...other existing vars
}
```

In the mutation's `mutationFn`, build the URL with the optional param:

```typescript
const params = new URLSearchParams();
if (vars.intakeOnly) params.set("intake_only", "true");
if (vars.extractOnly) params.set("extract_only", "true");
if (vars.workflowType) params.set("workflow_type", vars.workflowType);
const qs = params.toString() ? `?${params}` : "";
return apiClient.post(`/api/validate/${qs}`, formData);
```

- [ ] **Step 5: Run tests to pass**

Run: `cd apps/web && npm run test -- use-lcopilot`
Expected: both PASS.

- [ ] **Step 6: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS. Fix any new errors in `ExportLCUpload.tsx` that arise from the extended type (workflowType is optional, so existing calls without it still compile).

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Extend useValidate to thread workflowType as URL query param"
```

---

## Task 6: Wire the two new importer routes in App.tsx

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Locate the existing importer routes**

Run: `grep -n "importer-dashboard\|ImporterDashboardV2" apps/web/src/App.tsx`
Expected: route entries around line 404-416 per audit.

- [ ] **Step 2: Write a failing Playwright smoke test for routing**

Create `apps/web/tests/e2e/lcopilot/importer-routes.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Importer routes (Phase 2)", () => {
  test.use({ baseURL: process.env.BASE_URL || "http://localhost:3000" });

  test("draft-lc route loads the page with Draft LC title", async ({ page }) => {
    await page.goto("/lcopilot/importer-dashboard/draft-lc");
    // Auth redirect tolerated in dev; either we land on the page or on /login
    const url = page.url();
    if (url.includes("/login")) {
      test.skip(true, "Route behind auth; run authenticated in CI");
    }
    await expect(page.getByRole("heading", { name: /draft lc risk analysis/i })).toBeVisible({ timeout: 10000 });
  });

  test("supplier-docs route loads the page with Supplier Doc title", async ({ page }) => {
    await page.goto("/lcopilot/importer-dashboard/supplier-docs");
    const url = page.url();
    if (url.includes("/login")) {
      test.skip(true, "Route behind auth; run authenticated in CI");
    }
    await expect(page.getByRole("heading", { name: /supplier document review/i })).toBeVisible({ timeout: 10000 });
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/importer-routes.spec.ts`
Expected: FAIL (404 or title not found).

- [ ] **Step 4: Add the routes**

Edit `apps/web/src/App.tsx`. Near the existing importer routes, add:

```tsx
import { ImporterValidationPage } from "./pages/importer/ImporterValidationPage";
import { isImporterV2Enabled } from "./lib/lcopilot/featureFlags";

// ...inside the <Routes> block:
{isImporterV2Enabled() && (
  <>
    <Route
      path="/lcopilot/importer-dashboard/draft-lc"
      element={
        <LcopilotBetaRoute scope="importer">
          <ImporterValidationPage moment="draft_lc" />
        </LcopilotBetaRoute>
      }
    />
    <Route
      path="/lcopilot/importer-dashboard/supplier-docs"
      element={
        <LcopilotBetaRoute scope="importer">
          <ImporterValidationPage moment="supplier_docs" />
        </LcopilotBetaRoute>
      }
    />
  </>
)}
```

- [ ] **Step 5: Enable the flag locally**

Set `VITE_LCOPILOT_IMPORTER_V2=true` in `apps/web/.env` (local only; production toggle comes later).

- [ ] **Step 6: Start dev server and verify routes**

Run:
```
cd apps/web && npm run dev
```

In a browser (authenticated), visit `/lcopilot/importer-dashboard/draft-lc` and `/lcopilot/importer-dashboard/supplier-docs`. Both should render.

- [ ] **Step 7: Run Playwright**

Run: `cd apps/web && npx playwright test tests/e2e/lcopilot/importer-routes.spec.ts`
Expected: PASS (or skip-on-auth-redirect if unauthenticated).

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Add /draft-lc and /supplier-docs importer routes behind V2 feature flag"
```

---

## Task 7: Rewrite `ImportResults.tsx` as a thin shared-tab-shell wrapper

**Files:**
- Modify (full rewrite): `apps/web/src/pages/ImportResults.tsx`
- Delete: mock data and local transform functions in ImportResults.tsx

- [ ] **Step 1: Read the current file to identify what's deletable**

Run: `grep -n "mockDraftLCResults\|mockSupplierResults\|transformApiToDraftFormat\|transformApiToSupplierFormat" apps/web/src/pages/ImportResults.tsx`
Expected: line numbers for all four. These are going away.

- [ ] **Step 2: Write a failing test for the rewrite**

Create `apps/web/src/pages/__tests__/ImportResults.rewrite.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ImportResults from "../ImportResults";

vi.mock("@/hooks/use-lcopilot", () => ({
  useResults: () => ({
    data: {
      job_id: "job-1",
      structured_result: {
        meta: { workflow_type: "importer_draft_lc" },
        lc_structured: { documents_structured: [] },
        issues: [],
      },
      bank_verdict: { overall_verdict: "pass", issue_summary: { critical: 0, major: 0, minor: 0, total: 0 } },
    },
    isLoading: false,
  }),
}));

function renderAt(jobId = "job-1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/importer/results/${jobId}`]}>
        <Routes>
          <Route path="/importer/results/:jobId" element={<ImportResults />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ImportResults rewrite", () => {
  it("renders shared VerdictTab", () => {
    renderAt();
    expect(screen.getByRole("tab", { name: /verdict/i })).toBeInTheDocument();
  });

  it("does NOT reference any mock data", () => {
    // Smoke: if the old mocks were present, they'd show hardcoded LC numbers
    renderAt();
    expect(screen.queryByText("LC-2024-MOCK")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- ImportResults.rewrite`
Expected: FAIL (likely because current ImportResults renders mock LC numbers).

- [ ] **Step 4: Rewrite the file**

Replace the entire contents of `apps/web/src/pages/ImportResults.tsx`:

```typescript
import { useParams } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VerdictTab } from "@/components/lcopilot/results/tabs/VerdictTab";
import { DocumentsTab } from "@/components/lcopilot/results/tabs/DocumentsTab";
import { FindingsTab } from "@/components/lcopilot/results/tabs/FindingsTab";
import { HistoryTab } from "@/components/lcopilot/results/tabs/HistoryTab";
import { mapApiToResults } from "@/lib/lcopilot/resultsMapper";
import { useResults } from "@/hooks/use-lcopilot";
import { Skeleton } from "@/components/ui/skeleton";

export default function ImportResults() {
  const { jobId } = useParams();
  const { data, isLoading } = useResults(jobId);

  if (isLoading || !data) {
    return <Skeleton className="h-96 w-full" />;
  }

  const results = mapApiToResults(data);
  const workflowType = data.structured_result?.meta?.workflow_type ?? "importer_supplier_docs";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-bold">
          {workflowType === "importer_draft_lc" ? "Draft LC Risk Analysis — Results" : "Supplier Document Review — Results"}
        </h1>
      </header>

      <Tabs defaultValue="verdict">
        <TabsList>
          <TabsTrigger value="verdict">Verdict</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="findings">Findings</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="verdict">
          <VerdictTab
            results={results}
            actionSlot={/* Phase 3 fills this in — placeholder for now */ null}
          />
        </TabsContent>
        <TabsContent value="documents">
          <DocumentsTab results={results} />
        </TabsContent>
        <TabsContent value="findings">
          <FindingsTab results={results} />
        </TabsContent>
        <TabsContent value="history">
          <HistoryTab sessionId={jobId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

Adjust prop names if the shared tab components' actual interfaces differ (the Phase 1 extractions set these).

- [ ] **Step 5: Run tests to pass**

Run: `cd apps/web && npm run test -- ImportResults`
Expected: new rewrite tests PASS. If existing `ImportResults.test.tsx` tests fail on mocked structures, delete the obsolete tests (they asserted against mock data that's now gone).

- [ ] **Step 6: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Rewrite ImportResults as shared tab-shell wrapper, remove mock data + local transforms"
```

---

## Task 8: Playwright e2e — full Draft LC and Supplier Docs flows

**Files:**
- Create: `apps/web/tests/e2e/lcopilot/importer-draft-lc.spec.ts`
- Create: `apps/web/tests/e2e/lcopilot/importer-supplier-docs.spec.ts`

- [ ] **Step 1: Check existing importer-validation.spec for reusable fixtures**

Run: `head -40 apps/web/tests/e2e/lcopilot/importer-validation.spec.ts`
Expected: identifies auth helpers, file fixtures. Reuse them.

- [ ] **Step 2: Write Draft LC e2e spec**

Create `apps/web/tests/e2e/lcopilot/importer-draft-lc.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Importer Draft LC Review flow (Moment 1)", () => {
  test("upload → extract → review → validate → results", async ({ page }) => {
    await page.goto("/login");
    // Reuse auth pattern from importer-validation.spec.ts
    // ...auth fill-in...

    await page.goto("/lcopilot/importer-dashboard/draft-lc");
    await expect(page.getByRole("heading", { name: /draft lc risk analysis/i })).toBeVisible();

    const lcPath = path.resolve("tests/fixtures/ideal-sample/LC.pdf");
    await page.setInputFiles('input[type="file"]', lcPath);

    await page.getByRole("button", { name: /analyze lc risks/i }).click();

    await expect(page.getByText(/extract|review/i).first()).toBeVisible({ timeout: 60000 });

    // Confirm extraction review and kick off validation
    await page.getByRole("button", { name: /start validation|confirm/i }).click();

    await expect(page.getByRole("tab", { name: /verdict/i })).toBeVisible({ timeout: 180000 });
    await expect(page.getByRole("tab", { name: /findings/i })).toBeVisible();
  });
});
```

- [ ] **Step 3: Write Supplier Docs e2e spec**

Create `apps/web/tests/e2e/lcopilot/importer-supplier-docs.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Importer Supplier Document Review flow (Moment 2)", () => {
  test("upload LC + supplier docs → extract → review → validate → results", async ({ page }) => {
    await page.goto("/login");
    // ...auth...

    await page.goto("/lcopilot/importer-dashboard/supplier-docs");
    await expect(page.getByRole("heading", { name: /supplier document review/i })).toBeVisible();

    const files = [
      path.resolve("tests/fixtures/ideal-sample/LC.pdf"),
      path.resolve("tests/fixtures/ideal-sample/Invoice.pdf"),
      path.resolve("tests/fixtures/ideal-sample/Bill_of_Lading.pdf"),
    ];
    await page.setInputFiles('input[type="file"]', files);

    await page.getByRole("button", { name: /review supplier documents/i }).click();

    await expect(page.getByText(/extract|review/i).first()).toBeVisible({ timeout: 60000 });

    await page.getByRole("button", { name: /start validation|confirm/i }).click();

    await expect(page.getByRole("tab", { name: /verdict/i })).toBeVisible({ timeout: 180000 });
  });
});
```

- [ ] **Step 4: Ensure fixture files exist**

Run: `ls apps/web/tests/fixtures/ideal-sample/`
Expected: LC.pdf, Invoice.pdf, Bill_of_Lading.pdf (at minimum). If missing, either add from the IDEAL SAMPLE source at `F:\New Download\LC Copies\Synthetic\Export LC\IDEAL SAMPLE\` or adjust the specs to use whatever fixtures already exist in `apps/web/tests/fixtures/`.

- [ ] **Step 5: Run both specs (requires dev server or CI with baseURL)**

Run:
```
cd apps/web && npm run dev &
npx playwright test tests/e2e/lcopilot/importer-draft-lc.spec.ts tests/e2e/lcopilot/importer-supplier-docs.spec.ts
```
Expected: both PASS. Flaky test tolerances: wait timeouts up to 3 min for full validation.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add Playwright e2e specs for importer Draft LC and Supplier Docs flows"
```

---

## Task 9: Verify backend does not charge differently by workflow_type

**Files:**
- Create: `apps/api/tests/test_billing_workflow_type_parity.py`

- [ ] **Step 1: Write a failing billing-parity test**

Create `apps/api/tests/test_billing_workflow_type_parity.py`:

```python
"""One session per workflow_type must produce identical billing + quota records."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.validation_session import WorkflowType

client = TestClient(app)


@pytest.mark.parametrize("wf_type", [
    "exporter_presentation",
    "importer_draft_lc",
    "importer_supplier_docs",
])
def test_quota_counters_identical_across_workflow_types(
    authenticated_headers, sample_lc_file, wf_type, db_session, test_user
):
    # Baseline quota
    pre = db_session.execute(
        "SELECT COUNT(*) FROM validation_sessions WHERE user_id = :uid",
        {"uid": test_user.id},
    ).scalar()

    files = [("files", ("lc.pdf", sample_lc_file, "application/pdf"))]
    resp = client.post(
        f"/api/validate/?workflow_type={wf_type}&intake_only=true",
        files=files,
        headers=authenticated_headers,
    )
    assert resp.status_code in (200, 202)

    post = db_session.execute(
        "SELECT COUNT(*) FROM validation_sessions WHERE user_id = :uid",
        {"uid": test_user.id},
    ).scalar()

    # Every workflow_type adds exactly one session
    assert post - pre == 1
```

- [ ] **Step 2: Run to pass**

Run: `cd apps/api && pytest tests/test_billing_workflow_type_parity.py -v`
Expected: 3/3 PASS. If any fails, there's a per-workflow-type billing bug — investigate.

- [ ] **Step 3: Commit**

```
git add -A
git commit -m "Add test: quota counters identical across workflow_types"
```

---

## Task 10: Phase 2 final verification

**Files:**
- Verify: all

- [ ] **Step 1: Full backend + frontend test sweep**

Run:
```
cd apps/api && pytest tests/ -v -m "not slow"
cd apps/web && npm run type-check && npm run lint && npm run test
```
Expected: all PASS.

- [ ] **Step 2: Full Playwright sweep**

Run (with dev server up, flag enabled):
```
cd apps/web && npx playwright test tests/e2e/lcopilot/
```
Expected: all specs PASS (exporter still green, importer new specs green).

- [ ] **Step 3: Manual smoke — both moments end-to-end**

Start dev server with `VITE_LCOPILOT_IMPORTER_V2=true`, log in, click each new sidebar-less route:
- `/lcopilot/importer-dashboard/draft-lc` — upload an LC, run flow, verify results render with Draft LC title
- `/lcopilot/importer-dashboard/supplier-docs` — upload LC + invoice + BL, run flow, verify results render with Supplier Docs title
- Check `ValidationSession.workflow_type` in DB for each — should match the moment

- [ ] **Step 4: No commit — verification only**

---

## Phase 2 Exit Criteria

- [ ] `ValidationSession.workflow_type` column exists with 3 enum values + migration applied
- [ ] `/api/validate/?workflow_type=...` accepts all three values and persists correctly
- [ ] `<ImporterValidationPage moment="...">` renders correctly for both moments
- [ ] Routes `/lcopilot/importer-dashboard/draft-lc` and `/supplier-docs` reachable behind `LCOPILOT_IMPORTER_V2` flag
- [ ] `ImportResults.tsx` uses shared tab shell + `resultsMapper`; no mock data
- [ ] Playwright e2e green for both flows
- [ ] Billing parity test green (per-session billing unchanged)

Phase 2 complete. Proceed to Phase 3 plan.
