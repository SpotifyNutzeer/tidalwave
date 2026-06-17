<script lang="ts">
  import { browser } from '$app/environment';
  import { BarChart } from 'layerchart';
  import { weekdayName } from '$lib/format';
  let { days }: { days: number[] } = $props();
  const data = $derived(days.map((count, i) => ({ day: weekdayName(i), count })));
  const total = $derived(days.reduce((a, b) => a + b, 0));
</script>

<figure role="img" aria-label="Listens by weekday">
  <figcaption>By weekday</figcaption>
  <div class="chart">
    {#if browser}
      <BarChart {data} x="day" y="count" />
    {/if}
  </div>
  <span class="sr-only">{total} listens</span>
</figure>

<style>
  figure { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; margin: 0; }
  figcaption { color: var(--subtext); font-size: 1rem; margin-bottom: 0.5rem; }
  .chart { height: 200px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
