import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from './client';

const okJson = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }));

describe('api client', () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('me() returns the user and sends credentials', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ username: 'alice', is_admin: true }) as any);
    const me = await api.me();
    expect(me).toEqual({ username: 'alice', is_admin: true });
    expect(fetchMock).toHaveBeenCalledWith('/auth/me', expect.objectContaining({ credentials: 'include' }));
  });

  it('me() returns null on 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ detail: 'no' }, 401) as any);
    expect(await api.me()).toBeNull();
  });

  it('topArtists() passes the limit query param', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson([{ artist: 'A', count: 3 }]) as any);
    const rows = await api.topArtists(5);
    expect(rows[0]).toEqual({ artist: 'A', count: 3 });
    expect(fetchMock).toHaveBeenCalledWith('/stats/top-artists?limit=5', expect.objectContaining({ credentials: 'include' }));
  });

  it('createShare() posts and returns the token', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ share_token: 'TOK' }, 201) as any);
    expect(await api.createShare()).toEqual({ share_token: 'TOK' });
    expect(fetchMock).toHaveBeenCalledWith('/shares', expect.objectContaining({ method: 'POST', credentials: 'include' }));
  });

  it('shared.topArtists() throws on 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ detail: 'gone' }, 404) as any);
    await expect(api.shared.topArtists('TOK')).rejects.toThrow();
  });
});
