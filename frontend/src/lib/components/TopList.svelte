<script lang="ts">
  let { title, items }: { title: string; items: { label: string; count: number }[] } = $props();
  const max = $derived(items.reduce((m, i) => Math.max(m, i.count), 0) || 1);
</script>

<section class="glass">
  <h2>{title}</h2>
  {#if items.length === 0}
    <p class="empty">No data yet.</p>
  {:else}
    <ol>
      {#each items as item, i (item.label)}
        <li>
          <span class="bar" class:top={i === 0} style="width: {(item.count / max) * 100}%"></span>
          <span class="rank">{i + 1}</span>
          <span class="label">{item.label}</span>
          <span class="count">{item.count}</span>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  section {
    padding: 1.4rem 1.5rem;
  }
  h2 {
    font-size: 1.35rem;
    color: var(--text);
    margin: 0 0 1rem;
  }
  ol {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  li {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.45rem 0.6rem;
    border-radius: var(--r-sm);
    overflow: hidden;
  }
  .bar {
    position: absolute;
    inset: 0;
    background: var(--accent);
    opacity: 0.12;
    z-index: 0;
    border-radius: var(--r-sm);
    transition: width var(--dur) var(--ease-out);
  }
  .bar.top {
    opacity: 0.22;
  }
  .rank {
    z-index: 1;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-dim);
    min-width: 1.2rem;
  }
  .label {
    z-index: 1;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .count {
    z-index: 1;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }
  .empty {
    color: var(--text-dim);
    margin: 0;
  }
</style>
