import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import type { Bucket } from '$lib/api/client';

export type Range = 'day' | 'week' | 'month' | 'year' | 'all';
const KEY = 'tw-range';

export const RANGES: { value: Range; label: string }[] = [
  { value: 'day', label: 'Day' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Month' },
  { value: 'year', label: 'Year' },
  { value: 'all', label: 'All time' }
];

function initial(): Range {
  if (!browser) return 'month';
  const saved = localStorage.getItem(KEY);
  return RANGES.some((r) => r.value === saved) ? (saved as Range) : 'month';
}

/** Globally selected time window — drives every stats request across the site. */
export const range = writable<Range>(initial());

range.subscribe((value) => {
  if (browser) localStorage.setItem(KEY, value);
});

const WINDOW_MS: Record<Exclude<Range, 'all'>, number> = {
  day: 86_400_000,
  week: 7 * 86_400_000,
  month: 30 * 86_400_000,
  year: 365 * 86_400_000
};

/** Rolling-window `since` (ISO) for the selected range, or undefined for all-time. */
export function sinceFor(r: Range): string | undefined {
  if (r === 'all') return undefined;
  return new Date(Date.now() - WINDOW_MS[r]).toISOString();
}

/** A history/metrics bucket that keeps over-time graphs reasonably sampled. */
export function bucketFor(r: Range): Bucket {
  return r === 'year' || r === 'all' ? 'month' : 'day';
}
