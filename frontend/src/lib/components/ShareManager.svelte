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

<div class="share">
  {#if shareUrl}
    <span class="link">{shareUrl}</span>
    <button onclick={copy}>Copy</button>
    <button class="ghost" onclick={revoke}>Revoke</button>
  {:else}
    <button onclick={createShare} disabled={busy}>Share</button>
  {/if}
</div>

<style>
  .share {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .link {
    color: var(--accent-cyan);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    max-width: 14rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  button {
    background: var(--glass-bg-strong);
    color: var(--text);
    border: 1px solid var(--glass-border);
    border-radius: var(--r-pill);
    padding: 0.4rem 0.85rem;
    font-size: 0.82rem;
    cursor: pointer;
    transition: border-color var(--dur) var(--ease-out);
  }
  button:hover:not(:disabled) {
    border-color: var(--accent);
  }
  button:disabled {
    opacity: 0.6;
    cursor: default;
  }
  .ghost {
    color: var(--text-muted);
  }
</style>
