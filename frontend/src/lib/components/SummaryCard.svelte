<script lang="ts">
  let { total }: { total: number } = $props();
</script>

<div class="hero glass">
  <div class="stat">
    <span class="value">{total.toLocaleString()}</span>
    <span class="label">total listens</span>
  </div>
  <svg class="tide" viewBox="0 0 1200 24" preserveAspectRatio="none" aria-hidden="true">
    <path
      d="M0,12 C150,2 250,22 400,12 C550,2 650,22 800,12 C950,2 1050,22 1200,12"
      fill="none"
      stroke="var(--accent)"
      stroke-width="1.5"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</div>

<style>
  .hero {
    position: relative;
    overflow: hidden;
    padding: clamp(1.25rem, 3vw, 1.75rem) clamp(1.5rem, 4vw, 2.25rem);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
  }
  .stat {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.25rem 0.75rem;
  }
  .value {
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(2.5rem, 7vw, 3.75rem);
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-muted);
  }
  /* Tide-line: a quiet static accent, kept small so it reads as a mark, not a gimmick. */
  .tide {
    flex: 0 1 38%;
    height: 1.5rem;
    opacity: 0.4;
  }
  @media (max-width: 560px) {
    .tide {
      display: none;
    }
  }
</style>
