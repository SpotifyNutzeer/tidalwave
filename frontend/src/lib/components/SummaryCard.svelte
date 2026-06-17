<script lang="ts">
  let { total }: { total: number } = $props();
</script>

<div class="card">
  <span class="value">{total.toLocaleString()}</span>
  <span class="label">total listens</span>
</div>

<style>
  .card { background: var(--surface); border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.25rem; }
  .value { font-size: 2rem; font-weight: 700; color: var(--green); }
  .label { color: var(--subtext); }
</style>
