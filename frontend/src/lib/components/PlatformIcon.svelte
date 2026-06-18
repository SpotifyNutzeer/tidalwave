<script lang="ts">
  import type { PlatformId } from '$lib/platforms';

  let { id }: { id: PlatformId } = $props();

  // Brand glyphs from simple-icons (Spotify/Tidal/YouTube Music). Deezer was
  // removed from simple-icons, so its bar mark is reconstructed below.
  const PATHS: Partial<Record<PlatformId, string>> = {
    spotify:
      'M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z',
    tidal:
      'M12.012 3.992L8.008 7.996 4.004 3.992 0 7.996 4.004 12l4.004-4.004L12.012 12l-4.004 4.004 4.004 4.004 4.004-4.004L12.012 12l4.004-4.004-4.004-4.004zM16.042 7.996l3.979-3.979L24 7.996l-3.979 3.979z',
    youtube_music:
      'M12 0C5.376 0 0 5.376 0 12s5.376 12 12 12 12-5.376 12-12S18.624 0 12 0zm0 19.104c-3.924 0-7.104-3.18-7.104-7.104S8.076 4.896 12 4.896s7.104 3.18 7.104 7.104-3.18 7.104-7.104 7.104zm0-13.332c-3.432 0-6.228 2.796-6.228 6.228S8.568 18.228 12 18.228s6.228-2.796 6.228-6.228S15.432 5.772 12 5.772zM9.684 15.54V8.46L15.816 12l-6.132 3.54z'
  };
</script>

<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
  {#if id === 'deezer'}
    <!-- Deezer's equalizer-bar mark: a stepped grid of rounded bars. -->
    {#each [0, 5.15, 10.3, 15.45, 20.6] as x (x)}
      <rect {x} y="16" width="3.4" height="4" rx="0.6" />
    {/each}
    {#each [10.3, 15.45, 20.6] as x (x)}
      <rect {x} y="10" width="3.4" height="4" rx="0.6" />
    {/each}
    <rect x="20.6" y="4" width="3.4" height="4" rx="0.6" />
  {:else}
    <path d={PATHS[id]} />
  {/if}
</svg>

<style>
  svg {
    width: 100%;
    height: 100%;
    display: block;
  }
</style>
