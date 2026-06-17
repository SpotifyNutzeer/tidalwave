<script lang="ts">
  import ThemeToggle from './ThemeToggle.svelte';
  let { children }: { children?: import('svelte').Snippet } = $props();
</script>

<header>
  <a class="brand" href="/">tidalwave</a>
  <div class="actions">
    {@render children?.()}
    <ThemeToggle />
  </div>
</header>

<style>
  header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.5rem; background: var(--mantle); }
  .brand { color: var(--mauve); font-weight: 700; font-size: 1.25rem; text-decoration: none; }
  .actions { display: flex; gap: 0.75rem; align-items: center; }
</style>
