import { describe, expect, it } from 'vitest';
import { formatConditions } from '../utils';

describe('formatConditions', () => {
  it('normalizes serialized array-like 47A payload into readable items', () => {
    const input = "['DOC A REQUIRED'; 'DOC B REQUIRED'; 'NO ISRAELI FLAG VESSELS PERMITTED']";

    expect(formatConditions(input)).toEqual([
      'DOC A REQUIRED',
      'DOC B REQUIRED',
      'NO ISRAELI FLAG VESSELS PERMITTED',
    ]);
  });

  it('splits string values from array/object shapes and deduplicates', () => {
    const input = [
      { text: 'A; B' },
      { value: 'B|C' },
      'C',
    ];

    expect(formatConditions(input)).toEqual(['A', 'B', 'C']);
  });
});
