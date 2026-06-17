import { describe, it, expect } from 'vitest';
import { weekdayName } from './format';

describe('weekdayName', () => {
  it('maps index 0 to Monday and 6 to Sunday', () => {
    expect(weekdayName(0)).toBe('Mon');
    expect(weekdayName(6)).toBe('Sun');
  });
});
