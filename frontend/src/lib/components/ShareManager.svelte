<!-- frontend/src/lib/components/ShareManager.svelte -->
<script lang="ts">
  import { api } from '$lib/api/client';

  let token = $state<string | null>(null);
  let busy = $state(false);
  const shareUrl = $derived(token ? `${location.origin}/s/${token}` : null);

  async function createShare() {
    busy = true;
    try { token = (await api.createShare()).share_token; }
    finally { busy = false; }
  }
  async function revoke() {
    if (!token) return;
    await api.revokeShare(token);
    token = null;
  }
  async function copy() {
    if (shareUrl) await navigator.clipboard.writeText(shareUrl);
  }
</script>

{#if shareUrl}
  <span class="link">{shareUrl}</span>
  <button onclick={copy}>Copy</button>
  <button onclick={revoke}>Revoke</button>
{:else}
  <button onclick={createShare} disabled={busy}>Share</button>
{/if}

<style>
  .link { color: var(--blue); font-size: 0.85rem; }
  button { background: var(--surface); color: var(--text); border: 0; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; }
</style>
