<script lang="ts">
	import { asArray, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatBytes, formatTime } from '#lib/format';
	import { chartPoints, niceCeil, type ChartPadding } from '#lib/internet';

	let { history }: { history: unknown } = $props();

	const samples = $derived(
		asArray(history)
			.map((item) => {
				const row = asObject(item);
				return {
					at: asString(row.at, ''),
					size: asOptionalNumber(row.size_bytes)
				};
			})
			.filter((item): item is { at: string; size: number } => item.at !== '' && item.size !== null)
	);
	const width = 640;
	const height = 200;
	const padding: ChartPadding = { top: 16, right: 16, bottom: 28, left: 64 };
	const max = $derived(niceCeil(Math.max(1, ...samples.map((sample) => sample.size))));
	const points = $derived(
		chartPoints(
			samples.map((sample) => sample.size),
			width,
			height,
			max,
			padding
		)
	);
	const plotHeight = height - padding.top - padding.bottom;
	const gridLines = $derived(
		[0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
			y: padding.top + plotHeight - fraction * plotHeight,
			label: formatBytes(max * fraction)
		}))
	);

	function x(index: number): number {
		const plotWidth = width - padding.left - padding.right;
		return (
			padding.left +
			(samples.length <= 1 ? plotWidth / 2 : (index / (samples.length - 1)) * plotWidth)
		);
	}
</script>

{#if samples.length < 2}
	<div
		class="flex h-[200px] items-center justify-center rounded-brand border border-dashed border-line bg-surface-2/40 px-6 text-center"
	>
		<p class="text-[13px] text-ink-3">
			El histórico de tamaño se está recopilando. Se guarda una muestra cada 5 minutos.
		</p>
	</div>
{:else}
	<svg
		viewBox={`0 0 ${width} ${height}`}
		class="h-auto w-full overflow-visible"
		role="img"
		aria-label="Histórico del tamaño de la base de datos"
	>
		<title>Tamaño de la base de datos</title>

		{#each gridLines as line}
			<line
				x1={padding.left}
				y1={line.y}
				x2={width - padding.right}
				y2={line.y}
				class="stroke-line"
				stroke-width="1"
			/>
			<text x={padding.left - 8} y={line.y + 3} text-anchor="end" class="fill-ink-3 text-[10px]">
				{line.label}
			</text>
		{/each}

		<polyline
			{points}
			fill="none"
			class="stroke-accent"
			stroke-width="2.5"
			stroke-linejoin="round"
			stroke-linecap="round"
		/>

		{#if samples.length > 0}
			<text x={x(0)} y={height - 8} text-anchor="start" class="fill-ink-3 text-[10px]">
				{formatTime(samples[0].at)}
			</text>
			<text
				x={x(samples.length - 1)}
				y={height - 8}
				text-anchor="end"
				class="fill-ink-3 text-[10px]"
			>
				{formatTime(samples[samples.length - 1].at)}
			</text>
		{/if}
	</svg>
	<div class="mt-2 flex flex-wrap items-center gap-4 text-[12px] text-ink-3">
		<span class="inline-flex items-center gap-1.5">
			<span class="h-0.5 w-4 rounded-full bg-accent" aria-hidden="true"></span>
			Tamaño de la base
		</span>
		<span class="ml-auto">Últimas {samples.length} muestras · 24 h</span>
	</div>
{/if}
