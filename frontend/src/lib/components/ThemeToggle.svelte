<script lang="ts">
  import { theme, toggleTheme } from '$lib/stores/theme';
</script>

<button onclick={toggleTheme} aria-label="Toggle theme" title="Toggle theme">
  {$theme === 'mocha' ? '☾' : '☀'}
</button>

<style>
  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.2rem;
    height: 2.2rem;
    background: var(--glass-bg-strong);
    color: var(--text);
    border: 1px solid var(--glass-border);
    border-radius: var(--r-pill);
    font-size: 0.95rem;
    cursor: pointer;
    transition:
      border-color var(--dur) var(--ease-out),
      transform var(--dur) var(--ease-spring);
  }
  button:hover {
    border-color: var(--accent);
    transform: translateY(-1px);
  }
  @media (prefers-reduced-motion: reduce) {
    button {
      transition: none;
    }
  }
</style>
