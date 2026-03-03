import { z } from 'zod';

export const ExtractionStatusSchema = z.enum(['success', 'partial', 'failed']);
export type ExtractionStatus = z.infer<typeof ExtractionStatusSchema>;

export const ComplianceStatusSchema = z.enum(['clean', 'warning', 'reject']);
export type ComplianceStatus = z.infer<typeof ComplianceStatusSchema>;

export const PipelineVerificationStatusSchema = z.enum(['VERIFIED', 'UNVERIFIED']);
export type PipelineVerificationStatus = z.infer<typeof PipelineVerificationStatusSchema>;

export const CanonicalSemanticsSchema = z.object({
  extraction_status: ExtractionStatusSchema,
  compliance_status: ComplianceStatusSchema,
  pipeline_verification_status: PipelineVerificationStatusSchema,
  failed_reason: z.string().optional().nullable(),
}).superRefine((value, ctx) => {
  if (value.extraction_status === 'failed' && !value.failed_reason) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'failed_reason is required when extraction_status=failed',
      path: ['failed_reason'],
    });
  }
});

export type CanonicalSemantics = z.infer<typeof CanonicalSemanticsSchema>;

export const mapExtractionToUiStatus = (status: ExtractionStatus): 'success' | 'warning' | 'error' => {
  if (status === 'success') return 'success';
  if (status === 'partial') return 'warning';
  return 'error';
};
