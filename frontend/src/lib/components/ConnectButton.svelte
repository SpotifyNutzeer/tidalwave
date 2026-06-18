<script lang="ts">
  import { api } from '$lib/api/client';
</script>

<a class="connect" href={api.loginUrl()}>Connect with Last.fm</a>

<style>
  .connect {
    display: inline-block;
    background: var(--accent);
    color: var(--accent-contrast);
    font-weight: 600;
    padding: 0.8rem 1.6rem;
    border-radius: var(--r-pill);
    text-decoration: none;
    transition:
      transform var(--dur) var(--ease-spring),
      box-shadow var(--dur) var(--ease-out);
    box-shadow: 0 8px 24px -10px var(--accent);
  }
  .connect:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 30px -10px var(--accent);
  }
  @media (prefers-reduced-motion: reduce) {
    .connect {
      transition: none;
    }
  }
</style>
