const GENERIC_SPECIAL_CONDITION_PATTERNS = [
  /^additional conditions apply\.?$/i,
  /^additional conditions\.?$/i,
  /^see additional conditions\.?$/i,
];

export const SPECIAL_CONDITIONS_PLACEHOLDER_TEXT =
  "Field 47A references additional conditions, but no detailed clause text was extracted.";

export function isGenericSpecialConditionPlaceholder(value: string): boolean {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return false;
  }
  return GENERIC_SPECIAL_CONDITION_PATTERNS.some((pattern) => pattern.test(normalized));
}

export function summarizeSpecialConditions(
  values: Array<string | null | undefined> | null | undefined,
): { items: string[]; placeholderOnly: boolean } {
  const normalized = (values || [])
    .map((value) => String(value || "").trim())
    .filter((value, index, all) => value.length > 0 && all.indexOf(value) === index);
  const items = normalized.filter((value) => !isGenericSpecialConditionPlaceholder(value));
  return {
    items,
    placeholderOnly: normalized.length > 0 && items.length === 0,
  };
}
