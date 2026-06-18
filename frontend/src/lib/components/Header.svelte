<script lang="ts">
  import ThemeToggle from './ThemeToggle.svelte';
  let { children }: { children?: import('svelte').Snippet } = $props();
</script>

<header>
  <a class="brand" href="/">
    <span class="mark" aria-hidden="true"></span>
    tidalwave
  </a>
  <div class="actions">
    {@render children?.()}
    <ThemeToggle />
  </div>
</header>

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.85rem clamp(1rem, 4vw, 2rem);
    background: var(--glass-bg);
    border-bottom: 1px solid var(--glass-border);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    font-family: var(--font-display);
    font-size: 1.6rem;
    line-height: 1;
    color: var(--text);
    text-decoration: none;
    letter-spacing: -0.01em;
  }
  /* Tide mark: a small aqua disc with a soft accent halo. */
  .mark {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: var(--r-pill);
    background: var(--accent);
    box-shadow: 0 0 0 0.28rem var(--accent-soft);
  }
  .actions {
    display: flex;
    gap: 0.6rem;
    align-items: center;
  }
</style>
