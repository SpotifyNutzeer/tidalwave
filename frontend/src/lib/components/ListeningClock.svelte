<script lang="ts">
  let { hours }: { hours: number[] } = $props();
  const total = $derived(hours.reduce((a, b) => a + b, 0));
  const max = $derived(Math.max(1, ...hours));
</script>

<figure class="glass" role="img" aria-label="Listens by hour of day">
  <figcaption>By hour (UTC)</figcaption>
  <div class="barchart" aria-hidden="true">
    {#each hours as count, h (h)}
      <div class="col" title="{h}:00 — {count}">
        <div class="bar" style="height: {(count / max) * 100}%"></div>
      </div>
    {/each}
  </div>
  <div class="barlabels" aria-hidden="true">
    <span>0</span><span>6</span><span>12</span><span>18</span><span>23</span>
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
