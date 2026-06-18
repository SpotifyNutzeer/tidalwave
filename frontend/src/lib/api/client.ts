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
export interface TrackCount { track: string; artist: string; count: number; }
export interface AlbumCount { album: string; count: number; }
export interface HistoryPoint { period: string; count: number; }
export interface MetricPoint { period: string; listens: number; artists: number; albums: number; seconds: number; }
export interface RecentItem { track: string; artist: string; album: string | null; played_at: string; }
export interface Summary {
  total_listens: number;
  distinct_artists: number;
  distinct_tracks: number;
  distinct_albums: number;
  total_seconds: number;
}
export type Bucket = 'day' | 'week' | 'month';
export interface RangeParams { since?: string; until?: string; }

function qs(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v != null && v !== '');
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&');
}

export const api = {
  loginUrl: () => '/auth/login',

  async me(): Promise<UserInfo | null> {
    const res = await fetch('/auth/me', { credentials: 'include' });
    if (res.status === 401) return null;
    if (!res.ok) throw new ApiError(res.status, '/auth/me');
    return (await res.json()) as UserInfo;
  },

  summary: (p?: RangeParams) => get<Summary>(`/stats/summary${qs({ ...p })}`),
  topArtists: (limit?: number, p?: RangeParams) =>
    get<ArtistCount[]>(`/stats/top-artists${qs({ limit, ...p })}`),
  topTracks: (limit?: number, p?: RangeParams) =>
    get<TrackCount[]>(`/stats/top-tracks${qs({ limit, ...p })}`),
  topAlbums: (limit?: number, p?: RangeParams) =>
    get<AlbumCount[]>(`/stats/top-albums${qs({ limit, ...p })}`),
  clock: (p?: RangeParams) => get<number[]>(`/stats/clock${qs({ ...p })}`),
  weekday: (p?: RangeParams) => get<number[]>(`/stats/weekday${qs({ ...p })}`),
  history: (bucket: Bucket = 'day', p?: RangeParams) =>
    get<HistoryPoint[]>(`/stats/history${qs({ bucket, ...p })}`),
  metricsOverTime: (bucket: Bucket = 'day', p?: RangeParams) =>
    get<MetricPoint[]>(`/stats/metrics-over-time${qs({ bucket, ...p })}`),
  recent: (limit?: number) => get<RecentItem[]>(`/stats/recent${qs({ limit })}`),

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
    summary: (t: string) => get<Summary>(`/shared/${t}/summary`),
    topArtists: (t: string, limit?: number) => get<ArtistCount[]>(`/shared/${t}/top-artists${qs({ limit })}`),
    topTracks: (t: string, limit?: number) => get<TrackCount[]>(`/shared/${t}/top-tracks${qs({ limit })}`),
    topAlbums: (t: string, limit?: number) => get<AlbumCount[]>(`/shared/${t}/top-albums${qs({ limit })}`),
    clock: (t: string) => get<number[]>(`/shared/${t}/clock`),
    weekday: (t: string) => get<number[]>(`/shared/${t}/weekday`),
    history: (t: string, bucket: Bucket = 'day') => get<HistoryPoint[]>(`/shared/${t}/history?bucket=${bucket}`),
    metricsOverTime: (t: string, bucket: Bucket = 'day') => get<MetricPoint[]>(`/shared/${t}/metrics-over-time?bucket=${bucket}`),
    recent: (t: string) => get<RecentItem[]>(`/shared/${t}/recent`)
  }
};
