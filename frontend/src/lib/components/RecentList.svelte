<script lang="ts">
  import { formatDateTime } from '$lib/format';
  import type { RecentItem } from '$lib/api/client';
  let { items }: { items: RecentItem[] } = $props();
</script>

<section class="glass">
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
  section {
    padding: 1.4rem 1.5rem;
  }
  h2 {
    font-size: 1.35rem;
    color: var(--text);
    margin: 0 0 1rem;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
  }
  li {
    display: grid;
    grid-template-columns: 1fr auto;
    grid-template-areas: 'track time' 'artist time';
    column-gap: 0.75rem;
    align-items: baseline;
    padding: 0.55rem 0;
    border-top: 1px solid var(--glass-border);
  }
  li:first-child {
    border-top: 0;
  }
  .track {
    grid-area: track;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .artist {
    grid-area: artist;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
  time {
    grid-area: time;
    align-self: center;
    color: var(--text-dim);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .empty {
    color: var(--text-dim);
    margin: 0;
  }
</style>
