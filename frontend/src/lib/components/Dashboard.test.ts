import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Dashboard from './Dashboard.svelte';
import { api } from '$lib/api/client';

describe('Dashboard', () => {
  it('loads and renders stats sections', async () => {
    vi.spyOn(api, 'summary').mockResolvedValue({ total_listens: 42 });
    vi.spyOn(api, 'topArtists').mockResolvedValue([{ artist: 'Daft Punk', count: 10 }]);
    vi.spyOn(api, 'topTracks').mockResolvedValue([{ track: 'Aerodynamic', count: 6 }]);
    vi.spyOn(api, 'topAlbums').mockResolvedValue([{ album: 'Discovery', count: 8 }]);
    vi.spyOn(api, 'clock').mockResolvedValue(new Array(24).fill(0));
    vi.spyOn(api, 'weekday').mockResolvedValue(new Array(7).fill(0));
    vi.spyOn(api, 'history').mockResolvedValue([{ period: '2024-06-01T00:00:00', count: 3 }]);
    vi.spyOn(api, 'recent').mockResolvedValue([]);

    render(Dashboard);
    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument());
    expect(screen.getByText('Daft Punk')).toBeInTheDocument();
  });
});
