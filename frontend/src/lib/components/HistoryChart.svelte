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

<figure class="glass" role="img" aria-label="Listens over time">
  <figcaption class="head">
    <span class="title">Over time</span>
    <label>
      <span class="sr-only">Bucket</span>
      <select aria-label="Bucket" value={bucket} onchange={onChange}>
        <option value="day">Daily</option>
        <option value="week">Weekly</option>
        <option value="month">Monthly</option>
      </select>
    </label>
  </figcaption>
  <div class="chart tall">
    {#if browser}
      <AreaChart
        {data}
        x="date"
        y="count"
        props={{
          area: {
            fill: 'var(--accent)',
            fillOpacity: 0.2,
            line: { stroke: 'var(--accent)', 'stroke-width': 2 }
          }
        }}
      />
    {/if}
  </div>
</figure>

<style>
  figure {
    padding: 1.4rem 1.5rem;
    margin: 0;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }
  .title {
    font-family: var(--font-display);
    font-size: 1.35rem;
    color: var(--text);
  }
  select {
    background: var(--glass-bg-strong);
    color: var(--text);
    border: 1px solid var(--glass-border);
    border-radius: var(--r-pill);
    padding: 0.3rem 0.8rem;
    font-family: var(--font-body);
    font-size: 0.85rem;
    cursor: pointer;
  }
  .tall {
    height: 240px;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
