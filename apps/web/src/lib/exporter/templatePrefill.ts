export interface UploadTemplatePrefill {
  lcNumber?: string;
  issueDate?: string;
  notes?: string;
  appliedFields: string[];
}

const coerceText = (value: unknown): string | undefined => {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  return trimmed || undefined;
};

const normalizeDate = (value: unknown): string | undefined => {
  const text = coerceText(value);
  if (!text) {
    return undefined;
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }

  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) {
    return undefined;
  }

  return parsed.toISOString().slice(0, 10);
};

export const buildTemplateUploadPrefill = (
  fields: Record<string, unknown>,
  templateName?: string,
): UploadTemplatePrefill => {
  const appliedFields: string[] = [];
  const lcNumber = coerceText(fields.lc_number) ?? coerceText(fields.lcNumber);
  const issueDate =
    normalizeDate(fields.issue_date) ?? normalizeDate(fields.issueDate);
  const templateNotes =
    coerceText(fields.notes) ?? coerceText(fields.note) ?? undefined;

  if (lcNumber) {
    appliedFields.push('LC number');
  }

  if (issueDate) {
    appliedFields.push('issue date');
  }

  const contextPairs: Array<[string, unknown]> = [
    ['Beneficiary', fields.beneficiary],
    ['Amount', fields.amount],
    ['Expiry date', fields.expiry_date ?? fields.expiryDate],
    ['Shipment terms', fields.shipment_terms ?? fields.shipmentTerms],
    ['Consignee', fields.consignee],
    ['Shipper', fields.shipper],
    ['Incoterms', fields.incoterms],
    ['Currency', fields.currency],
  ];

  const contextLines = contextPairs
    .map(([label, value]) => {
      const text = coerceText(value);
      return text ? `${label}: ${text}` : null;
    })
    .filter((value): value is string => !!value);

  let notes = templateNotes;
  if (contextLines.length > 0) {
    const contextBlock = [
      `Template context${templateName ? ` (${templateName})` : ''}:`,
      ...contextLines.map((line) => `- ${line}`),
    ].join('\n');
    notes = notes ? `${notes}\n\n${contextBlock}` : contextBlock;
    appliedFields.push('template notes');
  } else if (notes) {
    appliedFields.push('notes');
  }

  return {
    lcNumber,
    issueDate,
    notes,
    appliedFields,
  };
};
