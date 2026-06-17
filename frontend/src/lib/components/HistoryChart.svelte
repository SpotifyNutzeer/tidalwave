<script lang="ts">
  import { AreaChart } from 'layerchart';
  import { browser } from '$app/environment';
  import type { Bucket, HistoryPoint } from '$lib/api/client';

  let { points, bucket, onBucketChange }:
    { points: HistoryPoint[]; bucket: Bucket; onBucketChange: (b: Bucket) => void } = $props();

  const data = $derived(points.map((p) => ({ date: new Date(p.period), count: p.count })));

  function onChange(e: Event) {
    onBucketChange((e.currentTarget as HTMLSelectElement).value as Bucket);
  }
</script>

<figure role="img" aria-label="Listens over time">
  <figcaption class="head">
    <span>Over time</span>
    <label>
      <span class="sr-only">Bucket</span>
      <select aria-label="Bucket" value={bucket} onchange={onChange}>
        <option value="day">Daily</option>
        <option value="week">Weekly</option>
        <option value="month">Monthly</option>
      </select>
    </label>
  </figcaption>
  <div class="chart">
    {#if browser}
      <AreaChart {data} x="date" y="count" />
    {/if}
  </div>
</figure>

<style>
  figure { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; margin: 0; }
  figcaption { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; color: var(--subtext); font-size: 1rem; }
  select { background: var(--mantle); color: var(--text); border: 0; border-radius: 6px; padding: 0.3rem 0.5rem; }
  .chart { height: 240px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
