import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import AreaTrend from './AreaTrend.svelte';

describe('AreaTrend', () => {
  it('renders an accessible region titled by its prop', () => {
    render(AreaTrend, { props: {
      title: 'Listens over time',
      points: [{ period: '2024-06-01T00:00:00', value: 3 }, { period: '2024-06-02T00:00:00', value: 5 }]
    } });
    expect(screen.getByRole('img', { name: /listens over time/i })).toBeInTheDocument();
  });

  it('shows a bucket selector when bucket controls are provided', async () => {
    const onBucketChange = vi.fn();
    render(AreaTrend, { props: {
      title: 'Over time',
      points: [{ period: '2024-06-01T00:00:00', value: 3 }],
      bucket: 'day',
      onBucketChange
    } });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /bucket/i }), 'week');
    expect(onBucketChange).toHaveBeenCalledWith('week');
  });
});
