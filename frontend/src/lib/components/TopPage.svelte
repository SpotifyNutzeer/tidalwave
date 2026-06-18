<script lang="ts">
  import { api, ApiError, type MetricPoint } from '$lib/api/client';
  import { loadMe } from '$lib/stores/auth';
  import { range, sinceFor, bucketFor } from '$lib/stores/range';
  import TopList from './TopList.svelte';
  import AreaTrend from './AreaTrend.svelte';

  let { kind }: { kind: 'artists' | 'tracks' | 'albums' } = $props();

  const TITLES = { artists: 'Top Artists', tracks: 'Top Tracks', albums: 'Top Albums' };
  const TRENDS = { artists: 'Artists over time', tracks: 'Listens over time', albums: 'Albums over time' };

  let items = $state<{ label: string; count: number }[]>([]);
  let metrics = $state<MetricPoint[]>([]);
  let error = $state(false);

  $effect(() => {
    const p = { since: sinceFor($range) };
    const bucket = bucketFor($range);
    const k = kind;
    (async () => {
      try {
        const metricsPromise = api.metricsOverTime(bucket, p);
        if (k === 'artists') {
          items = (await api.topArtists(100, p)).map((r) => ({ label: r.artist, count: r.count }));
        } else if (k === 'tracks') {
          items = (await api.topTracks(100, p)).map((r) => ({ label: r.track, count: r.count }));
        } else {
          items = (await api.topAlbums(100, p)).map((r) => ({
            label: r.album ?? 'Unknown album', count: r.count
          }));
        }
        metrics = await metricsPromise;
        error = false;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) await loadMe();
        else error = true;
      }
    })();
  });

  const trend = $derived(
    metrics.map((m) => ({
      period: m.period,
      value: kind === 'artists' ? m.artists : kind === 'albums' ? m.albums : m.listens
    }))
  );
</script>

{#if error}
  <p class="error">Could not load your stats. Please try again.</p>
{:else}
  <div class="dashboard">
    <AreaTrend title={TRENDS[kind]} points={trend} />
    <TopList title={TITLES[kind]} items={items} initial={1000} />
  </div>
{/if}

<style>
  .error {
    max-width: 1180px;
    margin: 0 auto;
    text-align: center;
    padding: 4rem 1.5rem;
    color: var(--text-muted);
  }
</style>
