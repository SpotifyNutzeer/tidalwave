<script lang="ts">
  import { weekdayName } from '$lib/format';
  let { days }: { days: number[] } = $props();
  const total = $derived(days.reduce((a, b) => a + b, 0));
  const max = $derived(Math.max(1, ...days));
</script>

<figure class="glass" role="img" aria-label="Listens by weekday">
  <figcaption>By weekday</figcaption>
  <div class="barchart" aria-hidden="true">
    {#each days as count, i (i)}
      <div class="col" title="{weekdayName(i)} — {count}">
        <div class="bar" style="height: {(count / max) * 100}%"></div>
      </div>
    {/each}
  </div>
  <div class="barlabels even" aria-hidden="true">
    {#each days as _, i (i)}
      <span>{weekdayName(i).slice(0, 1)}</span>
    {/each}
  </div>
  <span class="sr-only">{total} listens</span>
</figure>

<style>
  figure {
    padding: 1.4rem 1.5rem;
    margin: 0;
  }
  figcaption {
    font-family: var(--font-display);
    font-size: 1.35rem;
    color: var(--text);
    margin-bottom: 0.9rem;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
