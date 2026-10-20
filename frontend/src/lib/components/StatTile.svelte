<script lang="ts">
	let {
		label,
		value,
		hint = null
	}: { label: string; value: string | number; hint?: string | null } = $props();
</script>

<div class="rounded-brand border border-line bg-surface-2/45 px-4 py-3">
	<p class="text-[12px] font-medium tracking-wide text-ink-3 uppercase">{label}</p>
	<p class="tabular mt-1.5 text-[20px] leading-tight font-semibold text-ink">{value}</p>
	{#if hint}
		<p class="mt-1 text-[12px] text-ink-3">{hint}</p>
	{/if}
</div>
