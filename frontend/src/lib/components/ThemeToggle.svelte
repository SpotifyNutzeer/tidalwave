<script lang="ts">
  import { theme, toggleTheme } from '$lib/stores/theme';
</script>

<button onclick={toggleTheme} aria-label="Toggle theme" title="Toggle theme">
  {$theme === 'mocha' ? '☾' : '☀'}
</button>

<style>
  button { background: var(--surface); color: var(--text); border: 0; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; }
</style>
