// Thin typed wrapper over fetch. All calls are same-origin and send the session cookie.

export class ApiError extends Error {
  constructor(public status: number, public path: string) {
    super(`API ${status} for ${path}`);
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: 'include' });
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}

export interface UserInfo { username: string; is_admin: boolean; }
export interface ArtistCount { artist: string; count: number; }
export interface TrackCount { track: string; count: number; }
export interface AlbumCount { album: string; count: number; }
export interface HistoryPoint { period: string; count: number; }
export interface RecentItem { track: string; artist: string; album: string | null; played_at: string; }
export type Bucket = 'day' | 'week' | 'month';

const q = (limit?: number) => (limit == null ? '' : `?limit=${limit}`);

export const api = {
  loginUrl: () => '/auth/login',

  async me(): Promise<UserInfo | null> {
    const res = await fetch('/auth/me', { credentials: 'include' });
    if (res.status === 401) return null;
    if (!res.ok) throw new ApiError(res.status, '/auth/me');
    return (await res.json()) as UserInfo;
  },

  summary: () => get<{ total_listens: number }>('/stats/summary'),
  topArtists: (limit?: number) => get<ArtistCount[]>(`/stats/top-artists${q(limit)}`),
  topTracks: (limit?: number) => get<TrackCount[]>(`/stats/top-tracks${q(limit)}`),
  topAlbums: (limit?: number) => get<AlbumCount[]>(`/stats/top-albums${q(limit)}`),
  clock: () => get<number[]>('/stats/clock'),
  weekday: () => get<number[]>('/stats/weekday'),
  history: (bucket: Bucket = 'day') => get<HistoryPoint[]>(`/stats/history?bucket=${bucket}`),
  recent: (limit?: number) => get<RecentItem[]>(`/stats/recent${q(limit)}`),

  async createShare(): Promise<{ share_token: string }> {
    const res = await fetch('/shares', { method: 'POST', credentials: 'include' });
    if (!res.ok) throw new ApiError(res.status, '/shares');
    return (await res.json()) as { share_token: string };
  },
  async revokeShare(token: string): Promise<void> {
    const res = await fetch(`/shares/${token}`, { method: 'DELETE', credentials: 'include' });
    if (!res.ok) throw new ApiError(res.status, `/shares/${token}`);
  },

  shared: {
    summary: (t: string) => get<{ total_listens: number }>(`/shared/${t}/summary`),
    topArtists: (t: string) => get<ArtistCount[]>(`/shared/${t}/top-artists`),
    topTracks: (t: string) => get<TrackCount[]>(`/shared/${t}/top-tracks`),
    topAlbums: (t: string) => get<AlbumCount[]>(`/shared/${t}/top-albums`),
    clock: (t: string) => get<number[]>(`/shared/${t}/clock`),
    weekday: (t: string) => get<number[]>(`/shared/${t}/weekday`),
    history: (t: string, bucket: Bucket = 'day') => get<HistoryPoint[]>(`/shared/${t}/history?bucket=${bucket}`),
    recent: (t: string) => get<RecentItem[]>(`/shared/${t}/recent`)
  }
};
