<script lang="ts">
  import { api, ApiError, type Bucket } from '$lib/api/client';
  import { loadMe } from '$lib/stores/auth';
  import SummaryCard from './SummaryCard.svelte';
  import TopList from './TopList.svelte';
  import ListeningClock from './ListeningClock.svelte';
  import WeekdayChart from './WeekdayChart.svelte';
  import HistoryChart from './HistoryChart.svelte';
  import RecentList from './RecentList.svelte';

  let total = $state(0);
  let artists = $state<{ label: string; count: number }[]>([]);
  let tracks = $state<{ label: string; count: number }[]>([]);
  let albums = $state<{ label: string; count: number }[]>([]);
  let hours = $state<number[]>(new Array(24).fill(0));
  let days = $state<number[]>(new Array(7).fill(0));
  let history = $state<{ period: string; count: number }[]>([]);
  let recent = $state<{ track: string; artist: string; album: string | null; played_at: string }[]>([]);
  let bucket = $state<Bucket>('day');
  let error = $state(false);

  async function loadHistory(b: Bucket) {
    bucket = b;
    history = await api.history(b);
  }

  $effect(() => {
    (async () => {
      try {
        const [s, ar, tr, al, cl, wd, rc] = await Promise.all([
          api.summary(), api.topArtists(10), api.topTracks(10), api.topAlbums(10),
          api.clock(), api.weekday(), api.recent(20)
        ]);
        total = s.total_listens;
        artists = ar.map((x) => ({ label: x.artist, count: x.count }));
        tracks = tr.map((x) => ({ label: x.track, count: x.count }));
        albums = al.map((x) => ({ label: x.album, count: x.count }));
        hours = cl; days = wd; recent = rc;
        await loadHistory('day');
      } catch (e) {
        // Session expired/revoked mid-view: re-check auth so the page falls back to the connect CTA.
        if (e instanceof ApiError && e.status === 401) {
          await loadMe();
        } else {
          error = true;
        }
      }
    })();
  });
</script>

{#if error}
  <p class="error">Could not load your stats. Please try again.</p>
{:else}
<div class="dashboard">
  <SummaryCard {total} />
  <HistoryChart points={history} {bucket} onBucketChange={loadHistory} />
  <div class="row tops">
    <TopList title="Top Artists" items={artists} />
    <TopList title="Top Tracks" items={tracks} />
    <TopList title="Top Albums" items={albums} />
  </div>
  <div class="row charts">
    <ListeningClock {hours} />
    <WeekdayChart {days} />
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
