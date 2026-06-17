import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import HistoryChart from './HistoryChart.svelte';

describe('HistoryChart', () => {
  it('renders an accessible region and a bucket selector', async () => {
    const onBucketChange = vi.fn();
    render(HistoryChart, { props: {
      points: [{ period: '2024-06-01T00:00:00', count: 3 }, { period: '2024-06-02T00:00:00', count: 5 }],
      bucket: 'day',
      onBucketChange
    } });
    expect(screen.getByRole('img', { name: /listens over time/i })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /bucket/i }), 'week');
    expect(onBucketChange).toHaveBeenCalledWith('week');
  });
});
