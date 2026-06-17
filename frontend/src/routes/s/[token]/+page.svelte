<script lang="ts">
  import { api, type Bucket } from '$lib/api/client';
  import Header from '$lib/components/Header.svelte';
  import SummaryCard from '$lib/components/SummaryCard.svelte';
  import TopList from '$lib/components/TopList.svelte';
  import ListeningClock from '$lib/components/ListeningClock.svelte';
  import WeekdayChart from '$lib/components/WeekdayChart.svelte';
  import HistoryChart from '$lib/components/HistoryChart.svelte';
  import RecentList from '$lib/components/RecentList.svelte';

  let { data }: { data: { token: string } } = $props();
  const token = $derived(data.token);

  let error = $state(false);
  let total = $state(0);
  let artists = $state<{ label: string; count: number }[]>([]);
  let tracks = $state<{ label: string; count: number }[]>([]);
  let albums = $state<{ label: string; count: number }[]>([]);
  let hours = $state<number[]>(new Array(24).fill(0));
  let days = $state<number[]>(new Array(7).fill(0));
  let history = $state<{ period: string; count: number }[]>([]);
  let recent = $state<{ track: string; artist: string; album: string | null; played_at: string }[]>([]);
  let bucket = $state<Bucket>('day');

  async function loadHistory(b: Bucket) {
    bucket = b;
    history = await api.shared.history(token, b);
  }

  $effect(() => {
    (async () => {
      try {
        const [s, ar, tr, al, cl, wd, rc] = await Promise.all([
          api.shared.summary(token), api.shared.topArtists(token), api.shared.topTracks(token),
          api.shared.topAlbums(token), api.shared.clock(token), api.shared.weekday(token), api.shared.recent(token)
        ]);
        total = s.total_listens;
        artists = ar.map((x) => ({ label: x.artist, count: x.count }));
        tracks = tr.map((x) => ({ label: x.track, count: x.count }));
        albums = al.map((x) => ({ label: x.album, count: x.count }));
        hours = cl; days = wd; recent = rc;
        await loadHistory('day');
      } catch {
        error = true;
      }
    })();
  });
</script>

<Header />

{#if error}
  <p class="centered">This shared link was not found or has been revoked.</p>
{:else}
  <div class="grid">
    <SummaryCard {total} />
    <HistoryChart points={history} {bucket} onBucketChange={loadHistory} />
    <TopList title="Top Artists" items={artists} />
    <TopList title="Top Tracks" items={tracks} />
    <TopList title="Top Albums" items={albums} />
    <ListeningClock {hours} />
    <WeekdayChart {days} />
    <RecentList items={recent} />
  </div>
{/if}

<style>
  .centered { text-align: center; padding: 4rem 1.5rem; color: var(--subtext); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; padding: 1.5rem; }
</style>
