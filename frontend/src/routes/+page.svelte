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
    <h1>Your Tidal listening, tracked.</h1>
    <p>Connect your Last.fm account (where your Tidal scrobbles land) to see your stats.</p>
    <ConnectButton />
  </div>
{/if}

<style>
  .centered, .landing { text-align: center; padding: 4rem 1.5rem; }
  .landing h1 { color: var(--text); }
  .landing p { color: var(--subtext); }
</style>
