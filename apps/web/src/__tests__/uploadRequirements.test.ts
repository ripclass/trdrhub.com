import { describe, expect, it } from 'vitest';

import { getUploadRequirementsModel } from '@/lib/exporter/uploadRequirements';

describe('getUploadRequirementsModel', () => {
  it('prefers structured requirements over unstable legacy type/text array pairing', () => {
    const model = getUploadRequirementsModel({
      requiredDocumentTypes: ['beneficiary_certificate', 'other_specified_document'],
      documentsRequired: [
        'BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.',
        'ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.',
      ],
      requiredDocumentsDetailed: [
        {
          code: 'beneficiary_certificate',
          display_name: 'Beneficiary Certificate',
          raw_text: 'BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.',
        },
      ],
      requirementConditions: [
        'ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.',
      ],
      resolveLabel: (docType) => docType,
    });

    expect(model.documentRequirements).toHaveLength(1);
    expect(model.documentRequirements[0]).toMatchObject({
      type: 'beneficiary_certificate',
      label: 'Beneficiary Certificate',
      exactRequirement: 'BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.',
    });
    expect(model.additionalRequirements).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          category: 'lc_condition',
          detail: 'ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.',
        }),
      ]),
    );
  });
});
