import { normalizeDocumentType } from '@shared/types';
import type { LcClassificationRequiredDocument } from '@/types/lcopilot';

export interface UploadDocumentRequirement {
  key: string;
  type: string;
  label: string;
  exactRequirement: string;
}

export interface UploadAdditionalRequirement {
  key: string;
  label: string;
  detail: string;
  category: 'identifier' | 'lc_condition' | 'unmapped_requirement';
}

export interface UploadRequirementsModel {
  documentRequirements: UploadDocumentRequirement[];
  additionalRequirements: UploadAdditionalRequirement[];
}

const IDENTIFIER_REQUIREMENT_PATTERNS: Array<{ key: string; label: string; patterns: RegExp[] }> = [
  {
    key: 'exporter_bin',
    label: 'Exporter BIN',
    patterns: [/\bBIN\b/i, /business\s+identification\s+number/i],
  },
  {
    key: 'exporter_tin',
    label: 'Exporter TIN',
    patterns: [/\bTIN\b/i, /tax\s+identification\s+number/i],
  },
];

export function getUploadRequirementsModel(input: {
  requiredDocumentTypes?: string[] | null;
  documentsRequired?: string[] | null;
  requiredDocumentsDetailed?: LcClassificationRequiredDocument[] | null;
  requirementConditions?: string[] | null;
  unmappedRequirements?: string[] | null;
  specialConditions?: string[] | null;
  resolveLabel: (docType: string) => string;
}): UploadRequirementsModel {
  const requiredDocumentTypes = input.requiredDocumentTypes || [];
  const documentsRequired = input.documentsRequired || [];
  const requiredDocumentsDetailed = input.requiredDocumentsDetailed || [];
  const requirementConditions = input.requirementConditions || [];
  const unmappedRequirements = input.unmappedRequirements || [];
  const specialConditions = input.specialConditions || [];

  const documentRequirements = (() => {
    if (requiredDocumentsDetailed.length > 0) {
      const seen = new Set<string>();
      return requiredDocumentsDetailed.flatMap((requirement, index) => {
        const rawType = String(requirement?.code || '').trim();
        if (!rawType) return [];
        const normalizedType = normalizeDocumentType(rawType);
        const label =
          String(requirement?.display_name || '').trim() ||
          input.resolveLabel(normalizedType) ||
          rawType;
        const exactRequirement = String(
          requirement?.raw_text ||
            requirement?.exact_wording ||
            requirement?.display_name ||
            rawType,
        ).trim();
        const dedupeKey = `${normalizedType}:${exactRequirement.toLowerCase()}`;
        if (seen.has(dedupeKey)) return [];
        seen.add(dedupeKey);
        return [{
          key: `${normalizedType}-${index}`,
          type: normalizedType,
          label,
          exactRequirement,
        }];
      });
    }

    return requiredDocumentTypes.map((docType, index) => {
      const normalizedType = normalizeDocumentType(docType);
      const label = input.resolveLabel(normalizedType) || docType;
      const exactRequirement = String(documentsRequired[index] || '').trim();
      return {
        key: `${normalizedType}-${index}`,
        type: normalizedType,
        label,
        exactRequirement,
      };
    });
  })();

  const combinedTexts = [
    ...documentRequirements.map((requirement) => requirement.exactRequirement),
    ...requirementConditions,
    ...specialConditions,
    ...unmappedRequirements,
  ]
    .map((value) => String(value || '').trim())
    .filter((value, index, all) => value.length > 0 && all.indexOf(value) === index);

  const additionalRequirements: UploadAdditionalRequirement[] = [];
  const seen = new Set<string>();

  requirementConditions.forEach((text, index) => {
    const detail = String(text || '').trim();
    if (!detail) return;
    additionalRequirements.push({
      key: `lc-condition-${index}`,
      label: 'Document presentation condition',
      detail,
      category: 'lc_condition',
    });
  });

  unmappedRequirements.forEach((text, index) => {
    const detail = String(text || '').trim();
    if (!detail) return;
    additionalRequirements.push({
      key: `unmapped-requirement-${index}`,
      label: 'Requirement needs mapping',
      detail,
      category: 'unmapped_requirement',
    });
  });

  for (const text of combinedTexts) {
    for (const identifier of IDENTIFIER_REQUIREMENT_PATTERNS) {
      if (seen.has(identifier.key)) continue;
      if (identifier.patterns.some((pattern) => pattern.test(text))) {
        seen.add(identifier.key);
        additionalRequirements.push({
          key: identifier.key,
          label: identifier.label,
          detail: text,
          category: 'identifier',
        });
      }
    }
  }

  return {
    documentRequirements,
    additionalRequirements,
  };
}
