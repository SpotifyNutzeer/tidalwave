<script lang="ts">
  let { label, value, sub }: { label: string; value: string; sub?: string } = $props();
</script>

<div class="stat glass">
  <span class="value">{value}</span>
  <span class="label">{label}</span>
  {#if sub}<span class="sub">{sub}</span>{/if}
</div>

<style>
  .stat {
    padding: 1.25rem 1.4rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .value {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: clamp(2rem, 5vw, 2.85rem);
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    text-transform: lowercase;
    color: var(--text-muted);
  }
  .sub {
    font-size: 0.8rem;
    color: var(--text-dim);
  }
</style>
