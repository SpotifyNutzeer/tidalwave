<script lang="ts">
  let { title, items }: { title: string; items: { label: string; count: number }[] } = $props();
  const max = $derived(items.reduce((m, i) => Math.max(m, i.count), 0) || 1);
</script>

<section>
  <h2>{title}</h2>
  {#if items.length === 0}
    <p class="empty">No data yet.</p>
  {:else}
    <ol>
      {#each items as item (item.label)}
        <li>
          <span class="bar" style="width: {(item.count / max) * 100}%"></span>
          <span class="label">{item.label}</span>
          <span class="count">{item.count}</span>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  section { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; }
  h2 { font-size: 1rem; color: var(--subtext); margin: 0 0 0.75rem; }
  ol { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
  li { position: relative; display: flex; align-items: center; gap: 0.5rem; padding: 0.35rem 0.5rem; border-radius: 6px; overflow: hidden; }
  .bar { position: absolute; inset: 0; background: var(--mauve); opacity: 0.18; z-index: 0; }
  .label { z-index: 1; flex: 1; }
  .count { z-index: 1; color: var(--subtext); font-variant-numeric: tabular-nums; }
  .empty { color: var(--subtext); }
</style>
