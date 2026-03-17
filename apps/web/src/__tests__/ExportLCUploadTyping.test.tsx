import { describe, expect, it, vi } from "vitest";

vi.mock("react-dropzone", () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}));

vi.mock("@/hooks/use-lcopilot", () => ({
  useValidate: () => ({
    validate: vi.fn(),
    isLoading: false,
    clearError: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-lcopilot-quota", () => ({
  useLcopilotQuota: () => ({
    status: "ready",
    isExhausted: false,
    canValidate: true,
  }),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-drafts", () => ({
  useDrafts: () => ({
    saveDraft: vi.fn(),
    loadDraft: vi.fn(),
    removeDraft: vi.fn(),
    createDraft: vi.fn(),
    getDraft: vi.fn(),
    updateDraft: vi.fn(),
    markDraftSubmitted: vi.fn(),
    getAllDrafts: vi.fn(() => []),
    isLoading: false,
  }),
}));

vi.mock("@/hooks/use-versions", () => ({
  useVersions: () => ({
    checkLCExists: vi.fn().mockResolvedValue(null),
  }),
}));

vi.mock("@/api/sme-templates", () => ({
  smeTemplatesApi: {
    prefill: vi.fn(),
  },
}));

import {
  detectDocumentTypeFromFilename,
  formatWorkflowBadgeLabel,
  getQuickBadgeDocumentTypes,
} from "@/pages/ExportLCUpload";
import {
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_VALUES,
  getDocumentTypeIcon,
} from "@shared/types";
import { summarizeSpecialConditions } from "@/lib/exporter/specialConditions";

const MOJIBAKE_RE = /[âð]|ï¸|Ã|�/;

const uploadDocumentTypes = Object.values(DOCUMENT_TYPES)
  .filter((info) => info.value !== DOCUMENT_TYPE_VALUES.UNKNOWN)
  .map((info) => ({
    value: info.value,
    label: info.label,
    shortLabel: info.shortLabel,
    category: info.category,
    icon: getDocumentTypeIcon(info.value),
  }));

describe("ExportLCUpload typing helpers", () => {
  it("detects beneficiary certificate filenames reliably", () => {
    expect(detectDocumentTypeFromFilename("Beneficiary_Certificate.pdf").type).toBe(
      DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE,
    );
    expect(detectDocumentTypeFromFilename("beneficiary_statement_v2.PDF").type).toBe(
      DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE,
    );
  });

  it("maps weight-list filenames to weight certificate class for upload typing", () => {
    expect(detectDocumentTypeFromFilename("Weight_List.pdf").type).toBe(
      DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE,
    );
  });

  it("labels intake workflow as workflow instead of generic LC type", () => {
    expect(formatWorkflowBadgeLabel("unknown")).toBe("Workflow: unknown");
    expect(formatWorkflowBadgeLabel("export")).toBe("Workflow: export");
  });

  it("retains required beneficiary and weight classes in quick badges without silent truncation", () => {
    const shown = getQuickBadgeDocumentTypes(uploadDocumentTypes, [
      DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE,
      "weight_list",
    ]);
    const values = shown.map((item) => item.value);
    expect(values).toContain(DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE);
    expect(values).toContain(DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE);
    expect(shown.length).toBeLessThanOrEqual(18);
    expect(uploadDocumentTypes.length - shown.length).toBeGreaterThan(0);
  });

  it("does not treat generic additional-condition placeholders as extracted detail", () => {
    const summary = summarizeSpecialConditions(["ADDITIONAL CONDITIONS APPLY"]);
    expect(summary.items).toEqual([]);
    expect(summary.placeholderOnly).toBe(true);
  });
});

describe("shared document type icon mapping", () => {
  it("returns non-mojibake icons for key upload document classes", () => {
    const icons = [
      getDocumentTypeIcon(DOCUMENT_TYPE_VALUES.LETTER_OF_CREDIT),
      getDocumentTypeIcon(DOCUMENT_TYPE_VALUES.BILL_OF_LADING),
      getDocumentTypeIcon(DOCUMENT_TYPE_VALUES.INSURANCE_CERTIFICATE),
      getDocumentTypeIcon(DOCUMENT_TYPE_VALUES.BENEFICIARY_CERTIFICATE),
      getDocumentTypeIcon(DOCUMENT_TYPE_VALUES.WEIGHT_CERTIFICATE),
    ];
    for (const icon of icons) {
      expect(icon.trim().length).toBeGreaterThan(0);
      expect(MOJIBAKE_RE.test(icon)).toBe(false);
    }
  });
});
