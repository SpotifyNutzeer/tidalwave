<script lang="ts">
  import { onMount } from 'svelte';
  import { auth, loadMe } from '$lib/stores/auth';
  import Header from '$lib/components/Header.svelte';
  import ConnectButton from '$lib/components/ConnectButton.svelte';
  import Dashboard from '$lib/components/Dashboard.svelte';
  import ShareManager from '$lib/components/ShareManager.svelte';

  onMount(loadMe);
</script>

<Header>
  {#if $auth.user}<ShareManager />{/if}
</Header>

{#if $auth.loading}
  <p class="centered">Loading…</p>
{:else if $auth.user}
  <Dashboard />
{:else}
  <div class="landing">
    <p class="eyebrow">Tidal · via Last.fm</p>
    <h1>Your Tidal listening, tracked.</h1>
    <p class="lede">Connect your Last.fm account — where your Tidal scrobbles land — to see your stats roll in.</p>
    <ConnectButton />
  </div>
{/if}

<style>
  .centered {
    text-align: center;
    padding: 4rem 1.5rem;
    color: var(--text-muted);
  }
  .landing {
    max-width: 720px;
    margin: 0 auto;
    text-align: center;
    padding: clamp(3.5rem, 12vw, 8rem) 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.1rem;
  }
  .landing .eyebrow {
    margin: 0;
  }
  .landing h1 {
    font-size: clamp(2.6rem, 8vw, 4.75rem);
    color: var(--text);
    max-width: 14ch;
  }
  .landing .lede {
    margin: 0;
    max-width: 46ch;
    color: var(--text-muted);
    font-size: 1.05rem;
    line-height: 1.6;
  }
</style>
