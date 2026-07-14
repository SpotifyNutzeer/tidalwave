<script lang="ts">
  import '@fontsource-variable/jetbrains-mono';
  import '@fontsource-variable/jetbrains-mono/wght-italic.css';
  import '$lib/theme/tokens.css';
  let { children } = $props();
</script>

{@render children?.()}
