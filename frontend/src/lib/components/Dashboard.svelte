<script lang="ts">
  import { api, ApiError, type Summary, type MetricPoint, type RecentItem } from '$lib/api/client';
  import { loadMe } from '$lib/stores/auth';
  import { range, sinceFor, bucketFor } from '$lib/stores/range';
  import { formatCount, formatDuration } from '$lib/format';
  import StatCard from './StatCard.svelte';
  import AreaTrend from './AreaTrend.svelte';
  import TopList from './TopList.svelte';
  import ListeningClock from './ListeningClock.svelte';
  import WeekdayChart from './WeekdayChart.svelte';
  import RecentList from './RecentList.svelte';

  const EMPTY: Summary = {
    total_listens: 0, distinct_artists: 0, distinct_tracks: 0, distinct_albums: 0, total_seconds: 0
  };

  let summary = $state<Summary>(EMPTY);
  let metrics = $state<MetricPoint[]>([]);
  let artists = $state<{ label: string; count: number }[]>([]);
  let tracks = $state<{ label: string; count: number }[]>([]);
  let albums = $state<{ label: string; count: number }[]>([]);
  let hours = $state<number[]>(new Array(24).fill(0));
  let days = $state<number[]>(new Array(7).fill(0));
  let recent = $state<RecentItem[]>([]);
  let error = $state(false);

  $effect(() => {
    const p = { since: sinceFor($range) };
    const bucket = bucketFor($range);
    (async () => {
      try {
        const [s, m, ar, tr, al, cl, wd, rc] = await Promise.all([
          api.summary(p), api.metricsOverTime(bucket, p),
          api.topArtists(5, p), api.topTracks(5, p), api.topAlbums(5, p),
          api.clock(p), api.weekday(p), api.recent(12)
        ]);
        summary = s;
        metrics = m;
        artists = ar.map((x) => ({ label: x.artist, count: x.count }));
        tracks = tr.map((x) => ({ label: x.track, count: x.count }));
        albums = al.map((x) => ({ label: x.album ?? 'Unknown album', count: x.count }));
        hours = cl; days = wd; recent = rc;
        error = false;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) await loadMe();
        else error = true;
      }
    })();
  });

  const listensTrend = $derived(metrics.map((m) => ({ period: m.period, value: m.listens })));
  const timeTrend = $derived(metrics.map((m) => ({ period: m.period, value: m.seconds })));
  const artistsTrend = $derived(metrics.map((m) => ({ period: m.period, value: m.artists })));
  const timePending = $derived(summary.total_listens > 0 && summary.total_seconds === 0);
</script>

{#if error}
  <p class="error">Could not load your stats. Please try again.</p>
{:else}
  <div class="dashboard">
    <div class="row stats">
      <StatCard label="Songs listened" value={formatCount(summary.total_listens)} />
      <StatCard
        label="Time listened"
        value={formatDuration(summary.total_seconds)}
        sub={timePending ? 'resolving durations…' : undefined}
      />
      <StatCard label="Artists" value={formatCount(summary.distinct_artists)} />
      <StatCard label="Albums" value={formatCount(summary.distinct_albums)} />
    </div>
    <div class="row trends">
      <AreaTrend title="Listens over time" points={listensTrend} />
      <AreaTrend title="Time listened" points={timeTrend} formatValue={formatDuration} />
      <AreaTrend title="Artists over time" points={artistsTrend} />
    </div>
    <div class="row charts">
      <ListeningClock {hours} />
      <WeekdayChart {days} />
    </div>
    <div class="row tops">
      <TopList title="Top Artists" items={artists} href="/artists" />
      <TopList title="Top Tracks" items={tracks} href="/tracks" />
      <TopList title="Top Albums" items={albums} href="/albums" />
    </div>
    <RecentList items={recent} />
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
