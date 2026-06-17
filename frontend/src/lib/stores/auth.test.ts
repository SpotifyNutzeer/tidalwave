import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { auth, loadMe } from './auth';
import { api } from '$lib/api/client';

describe('auth store', () => {
  beforeEach(() => { auth.set({ user: null, loading: false }); });

  it('loadMe populates the user when logged in', async () => {
    vi.spyOn(api, 'me').mockResolvedValue({ username: 'alice', is_admin: true });
    await loadMe();
    expect(get(auth).user).toEqual({ username: 'alice', is_admin: true });
    expect(get(auth).loading).toBe(false);
  });

  it('loadMe leaves user null when anonymous', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null);
    await loadMe();
    expect(get(auth).user).toBeNull();
  });
});
