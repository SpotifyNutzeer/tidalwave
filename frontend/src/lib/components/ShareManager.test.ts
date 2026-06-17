import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import ShareManager from './ShareManager.svelte';
import { api } from '$lib/api/client';

describe('ShareManager', () => {
  it('creates a share and shows the public link', async () => {
    vi.spyOn(api, 'createShare').mockResolvedValue({ share_token: 'TOK123' });
    render(ShareManager);
    await userEvent.click(screen.getByRole('button', { name: /share/i }));
    const link = await screen.findByText(/\/s\/TOK123$/);
    expect(link).toBeInTheDocument();
  });
});
