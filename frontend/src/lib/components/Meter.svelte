<script lang="ts">
	import type { ModuleStatus } from '#lib/modules';
	import { formatPercent } from '#lib/format';

	let {
		label,
		value,
		detail = null,
		status = 'ok',
		unit = '%'
	}: {
		label: string;
		value: number;
		detail?: string | null;
		status?: ModuleStatus;
		unit?: string;
	} = $props();

	const width = $derived(`${Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0))}%`);
	const tone = $derived(
		status === 'critical'
			? 'bg-danger'
			: status === 'warn'
				? 'bg-warning'
				: status === 'ok'
					? 'bg-success'
					: 'bg-ink-3/50'
	);
</script>

<div>
	<div class="flex items-baseline justify-between gap-3">
		<span class="text-[14px] font-medium text-ink">{label}</span>
		<span class="tabular text-[14px] font-semibold text-ink">
			{unit === '%' ? formatPercent(value, 1) : `${value} ${unit}`}
		</span>
	</div>
	<div class="mt-2 h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
		<div
			class="h-full rounded-full transition-[width] duration-500 ease-brand {tone}"
			style:width
		></div>
	</div>
	{#if detail}
		<p class="mt-1.5 text-[12px] text-ink-3">{detail}</p>
	{/if}
</div>
