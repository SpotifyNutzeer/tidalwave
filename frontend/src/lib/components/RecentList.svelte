<script lang="ts">
  import { formatDateTime } from '$lib/format';
  import type { RecentItem } from '$lib/api/client';
  let { items }: { items: RecentItem[] } = $props();
</script>

<section>
  <h2>Recent</h2>
  {#if items.length === 0}
    <p class="empty">No data yet.</p>
  {:else}
    <ul>
      {#each items as item (item.played_at + item.track)}
        <li>
          <span class="track">{item.track}</span>
          <span class="artist">{item.artist}</span>
          <time>{formatDateTime(item.played_at)}</time>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  section { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; }
  h2 { font-size: 1rem; color: var(--subtext); margin: 0 0 0.75rem; }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
  li { display: grid; grid-template-columns: 1fr auto auto; gap: 0.75rem; align-items: baseline; }
  .artist { color: var(--subtext); }
  time { color: var(--subtext); font-variant-numeric: tabular-nums; }
  .empty { color: var(--subtext); }
</style>
