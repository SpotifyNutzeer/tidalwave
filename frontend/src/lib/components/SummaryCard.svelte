<script lang="ts">
  let { total }: { total: number } = $props();
</script>

<div class="hero glass">
  <div class="stat">
    <span class="value">{total.toLocaleString()}</span>
    <span class="label">total listens</span>
  </div>
  <svg class="tide" viewBox="0 0 1200 60" preserveAspectRatio="none" aria-hidden="true">
    <path
      d="M0,30 C150,4 250,56 400,30 C550,4 650,56 800,30 C950,4 1050,56 1200,30"
      fill="none"
      stroke="var(--accent)"
      stroke-width="2"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</div>

<style>
  .hero {
    position: relative;
    overflow: hidden;
    padding: clamp(1.5rem, 4vw, 2.5rem) clamp(1.5rem, 4vw, 2.75rem);
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }
  .stat {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.25rem 1rem;
  }
  .value {
    font-family: var(--font-display);
    font-weight: 400;
    font-size: clamp(3.25rem, 11vw, 6rem);
    line-height: 0.9;
    letter-spacing: -0.02em;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-muted);
  }
  /* Tide-line: the signature wave under the headline number. */
  .tide {
    width: 100%;
    height: 2.25rem;
    opacity: 0.5;
    animation: swell 9s var(--ease-out) infinite alternate;
  }
  @keyframes swell {
    from { transform: translateX(-2%) scaleY(0.85); }
    to   { transform: translateX(2%) scaleY(1.15); }
  }
  @media (prefers-reduced-motion: reduce) {
    .tide { animation: none; }
  }
</style>
