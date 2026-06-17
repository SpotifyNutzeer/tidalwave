import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Page from './+page.svelte';
import { api } from '$lib/api/client';

describe('home page', () => {
  it('renders the landing page when logged out', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null);
    render(Page);
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /your tidal listening/i })).toBeInTheDocument()
    );
  });
});
