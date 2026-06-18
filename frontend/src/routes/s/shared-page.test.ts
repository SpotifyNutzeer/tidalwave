import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SharedPage from './[token]/+page.svelte';
import { api } from '$lib/api/client';

describe('shared dashboard page', () => {
  it('renders shared stats for a valid token', async () => {
    vi.spyOn(api.shared, 'summary').mockResolvedValue({
      total_listens: 7, distinct_artists: 1, distinct_tracks: 1, distinct_albums: 0, total_seconds: 0
    });
    vi.spyOn(api.shared, 'topArtists').mockResolvedValue([{ artist: 'Kavinsky', count: 3 }]);
    vi.spyOn(api.shared, 'topTracks').mockResolvedValue([]);
    vi.spyOn(api.shared, 'topAlbums').mockResolvedValue([]);
    vi.spyOn(api.shared, 'clock').mockResolvedValue(new Array(24).fill(0));
    vi.spyOn(api.shared, 'weekday').mockResolvedValue(new Array(7).fill(0));
    vi.spyOn(api.shared, 'metricsOverTime').mockResolvedValue([]);
    vi.spyOn(api.shared, 'recent').mockResolvedValue([]);

    render(SharedPage, { props: { data: { token: 'TOK' } } });
    await waitFor(() => expect(screen.getByText('7')).toBeInTheDocument());
    expect(screen.getByText('Kavinsky')).toBeInTheDocument();
  });

  it('shows a not-found message when the token is invalid', async () => {
    vi.spyOn(api.shared, 'summary').mockRejectedValue(new Error('404'));
    render(SharedPage, { props: { data: { token: 'BAD' } } });
    await waitFor(() => expect(screen.getByText(/not found|revoked/i)).toBeInTheDocument());
  });
});
