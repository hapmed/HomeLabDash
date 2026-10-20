<script lang="ts">
	import { formatNumber, formatTime } from '#lib/format';
	import {
		chartMax,
		chartPoints,
		parseHistory,
		type ChartPadding,
		type SpeedSample
	} from '#lib/internet';

	let { history }: { history: unknown } = $props();

	const samples = $derived(parseHistory(history));
	const width = 640;
	const height = 220;
	const padding: ChartPadding = { top: 16, right: 16, bottom: 28, left: 48 };
	const max = $derived(chartMax(samples));
	const downloads = $derived(samples.map((sample: SpeedSample) => sample.download_mbps ?? 0));
	const uploads = $derived(samples.map((sample: SpeedSample) => sample.upload_mbps ?? 0));
	const plotHeight = height - padding.top - padding.bottom;

	const downPoints = $derived(chartPoints(downloads, width, height, max, padding));
	const upPoints = $derived(chartPoints(uploads, width, height, max, padding));
	const gridLines = $derived(
		[0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
			y: padding.top + plotHeight - fraction * plotHeight,
			label: formatNumber(max * fraction, 0)
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
		class="flex h-[220px] items-center justify-center rounded-brand border border-dashed border-line bg-surface-2/40 px-6 text-center"
	>
		<p class="text-[13px] text-ink-3">
			Aún no hay suficientes pruebas para dibujar el histórico. La primera se ejecuta al arrancar y
			después cada hora.
		</p>
	</div>
{:else}
	<div>
		<svg
			viewBox={`0 0 ${width} ${height}`}
			class="h-auto w-full overflow-visible"
			role="img"
			aria-label="Histórico de velocidad de bajada y subida en Mbps"
		>
			<title>Histórico de velocidad de Internet</title>

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
				points={downPoints}
				fill="none"
				class="stroke-accent"
				stroke-width="2.5"
				stroke-linejoin="round"
				stroke-linecap="round"
			/>
			<polyline
				points={upPoints}
				fill="none"
				class="stroke-accent-2"
				stroke-width="2"
				stroke-linejoin="round"
				stroke-linecap="round"
				stroke-dasharray="5 4"
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
				Bajada
			</span>
			<span class="inline-flex items-center gap-1.5">
				<span class="h-0.5 w-4 rounded-full bg-accent-2" aria-hidden="true"></span>
				Subida
			</span>
			<span class="ml-auto">Mbps · últimas {samples.length} pruebas</span>
		</div>
	</div>
{/if}
