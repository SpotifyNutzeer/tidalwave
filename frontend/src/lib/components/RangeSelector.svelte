<script lang="ts">
  import { range, RANGES } from '$lib/stores/range';
</script>

<div class="ranges" role="group" aria-label="Time range">
  {#each RANGES as r (r.value)}
    <button
      type="button"
      class:active={$range === r.value}
      aria-pressed={$range === r.value}
      onclick={() => range.set(r.value)}
    >
      {r.label}
    </button>
  {/each}
</div>

<style>
  .ranges {
    display: inline-flex;
    gap: 0.15rem;
    padding: 0.2rem;
    border: 1px solid var(--glass-border);
    border-radius: var(--r-pill);
    background: var(--glass-bg);
  }
  button {
    border: 0;
    background: none;
    cursor: pointer;
    padding: 0.32rem 0.7rem;
    border-radius: var(--r-pill);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    white-space: nowrap;
    transition: color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
  }
  button:hover {
    color: var(--text);
  }
  button.active {
    background: var(--accent);
    color: var(--accent-contrast);
  }
</style>
