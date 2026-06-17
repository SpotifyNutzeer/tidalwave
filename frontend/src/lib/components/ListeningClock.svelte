<script lang="ts">
  import { browser } from '$app/environment';
  import { BarChart } from 'layerchart';
  let { hours }: { hours: number[] } = $props();
  const data = $derived(hours.map((count, h) => ({ hour: `${h}`, count })));
  const total = $derived(hours.reduce((a, b) => a + b, 0));
</script>

<figure role="img" aria-label="Listens by hour of day">
  <figcaption>By hour (UTC)</figcaption>
  <div class="chart">
    {#if browser}
      <BarChart {data} x="hour" y="count" />
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
