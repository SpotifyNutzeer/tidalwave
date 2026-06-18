import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Dashboard from './Dashboard.svelte';
import { api } from '$lib/api/client';

describe('Dashboard', () => {
  it('loads and renders the headline stats and top lists', async () => {
    vi.spyOn(api, 'summary').mockResolvedValue({
      total_listens: 42, distinct_artists: 5, distinct_tracks: 30, distinct_albums: 8, total_seconds: 7200
    });
    // Empty trend → charts show no y-axis numbers, so the stat-card values below stay unique.
    vi.spyOn(api, 'metricsOverTime').mockResolvedValue([]);
    vi.spyOn(api, 'topArtists').mockResolvedValue([{ artist: 'Daft Punk', count: 10 }]);
    vi.spyOn(api, 'topTracks').mockResolvedValue([{ track: 'Aerodynamic', artist: 'Daft Punk', count: 6 }]);
    vi.spyOn(api, 'topAlbums').mockResolvedValue([{ album: 'Discovery', count: 8 }]);
    vi.spyOn(api, 'clock').mockResolvedValue(new Array(24).fill(0));
    vi.spyOn(api, 'weekday').mockResolvedValue(new Array(7).fill(0));
    vi.spyOn(api, 'recent').mockResolvedValue([]);

    render(Dashboard);
    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument());
    expect(screen.getByText('Daft Punk')).toBeInTheDocument();
    expect(screen.getByText('2h 0m')).toBeInTheDocument(); // 7200s formatted
  });
});
