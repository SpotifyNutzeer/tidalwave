import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import TopPage from './TopPage.svelte';
import { api } from '$lib/api/client';

describe('TopPage', () => {
  it('labels tracks with their artist so same-titled songs are distinguishable', async () => {
    vi.spyOn(api, 'metricsOverTime').mockResolvedValue([]);
    vi.spyOn(api, 'topTracks').mockResolvedValue([
      { track: 'Paradise', artist: 'Coldplay', count: 12 },
      { track: 'Paradise', artist: 'George Ezra', count: 7 }
    ]);

    render(TopPage, { props: { kind: 'tracks' } });
    await waitFor(() => expect(screen.getByText('Paradise — Coldplay')).toBeInTheDocument());
    expect(screen.getByText('Paradise — George Ezra')).toBeInTheDocument();
  });

  it('labels shared tracks with their artist as well', async () => {
    vi.spyOn(api.shared, 'metricsOverTime').mockResolvedValue([]);
    vi.spyOn(api.shared, 'topTracks').mockResolvedValue([
      { track: 'Paradise', artist: 'Coldplay', count: 12 }
    ]);

    render(TopPage, { props: { kind: 'tracks', token: 'TOK' } });
    await waitFor(() => expect(screen.getByText('Paradise — Coldplay')).toBeInTheDocument());
  });
});
