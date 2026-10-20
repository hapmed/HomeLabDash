<script lang="ts">
	import { ArrowUpRight } from '@lucide/svelte';

	import type { ModuleCard as ModuleCardType } from '#lib/modules';
	import { formatPercent } from '#lib/format';
	import ModuleIcon from './ModuleIcon.svelte';
	import StatusBadge from './StatusBadge.svelte';

	let { card }: { card: ModuleCardType } = $props();

	const numericValue = $derived(typeof card.summary.value === 'number' ? card.summary.value : null);
	const showMeter = $derived(card.summary.unit === '%' && numericValue !== null);
	const meterWidth = $derived(`${Math.max(0, Math.min(100, numericValue ?? 0))}%`);
	const meterTone = $derived(
		card.status === 'critical'
			? 'bg-danger'
			: card.status === 'warn'
				? 'bg-warning'
				: card.status === 'ok'
					? 'bg-success'
					: 'bg-ink-3/50'
	);
</script>

<a
	href={`/modulo/${card.id}`}
	class="group relative flex min-h-[196px] flex-col gap-4 rounded-brand-lg border border-line bg-surface p-5 no-underline transition-[transform,box-shadow,border-color] duration-300 ease-brand hover:-translate-y-0.5 hover:border-accent/35 hover:shadow-[0_18px_50px_-30px_rgba(0,0,0,0.35)]"
	aria-label={`${card.name}: ${card.summary.value}${card.summary.unit ?? ''}. Abrir detalle`}
>
	<div class="flex items-start justify-between gap-3">
		<span
			class="inline-flex h-10 w-10 items-center justify-center rounded-[12px] bg-surface-2 text-ink-2 transition-colors group-hover:text-accent"
		>
			<ModuleIcon name={card.icon} />
		</span>
		<StatusBadge status={card.status} compact />
	</div>

	<div class="flex flex-1 flex-col">
		<h2 class="text-[17px] font-semibold text-ink">{card.name}</h2>
		<p class="mt-0.5 text-[13px] leading-5 text-ink-2">{card.description}</p>

		<div class="mt-4 flex items-baseline gap-1.5">
			<span class="tabular text-[32px] leading-none font-semibold tracking-tight text-ink">
				{typeof card.summary.value === 'number'
					? card.summary.value.toLocaleString('es-ES', { maximumFractionDigits: 1 })
					: card.summary.value}
			</span>
			{#if card.summary.unit}
				<span class="text-[15px] font-medium text-ink-2">{card.summary.unit}</span>
			{/if}
			<span class="ml-1 text-[13px] text-ink-3">{card.summary.label}</span>
		</div>

		{#if showMeter}
			<div class="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
				<div
					class="h-full rounded-full transition-[width] duration-500 ease-brand {meterTone}"
					style:width={meterWidth}
				></div>
			</div>
		{/if}

		{#if card.summary.detail}
			<p class="mt-3 text-[12px] leading-5 text-ink-3">{card.summary.detail}</p>
		{/if}
	</div>

	<span
		class="absolute right-4 bottom-4 inline-flex items-center gap-1 text-[12px] font-medium text-ink-3 opacity-0 transition-opacity group-hover:opacity-100"
		aria-hidden="true"
	>
		Ver detalle
		<ArrowUpRight size={14} />
	</span>
</a>
