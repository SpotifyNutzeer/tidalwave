<script lang="ts">
  import { api } from '$lib/api/client';
</script>

<a class="connect" href={api.loginUrl()}>Connect with Last.fm</a>

<style>
  .connect { display: inline-block; background: var(--mauve); color: var(--base); font-weight: 600; padding: 0.6rem 1rem; border-radius: 8px; text-decoration: none; }
</style>
