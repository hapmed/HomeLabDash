<script lang="ts">
	import { ChartNoAxesColumn, RotateCw } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { api } from '#lib/api';
	import { formatBytes, formatNumber, formatPercent, formatTime } from '#lib/format';
	import { HISTORY_METRICS, type HistoryMetric, type HistorySample } from '#lib/history';
	import Sparkline from '#lib/components/Sparkline.svelte';

	let { moduleId }: { moduleId: string } = $props();

	const ranges = [
		{ hours: 24, label: '24 h' },
		{ hours: 168, label: '7 días' },
		{ hours: 720, label: '30 días' }
	];

	let hours = $state(24);
	let samples = $state<HistorySample[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let requestId = 0;

	const metrics = $derived(HISTORY_METRICS[moduleId] ?? []);
	const lastAt = $derived(samples.length > 0 ? samples[samples.length - 1].at : null);

	async function load(nextHours = hours) {
		const current = ++requestId;
		hours = nextHours;
		loading = true;
		error = null;
		try {
			const result = await api.moduleHistory(moduleId, nextHours);
			if (current === requestId) samples = result;
		} catch {
			if (current === requestId) error = 'No se pudo cargar el histórico.';
		} finally {
			if (current === requestId) loading = false;
		}
	}

	function formatValue(value: number | undefined, metric: HistoryMetric): string {
		if (value === undefined || !Number.isFinite(value)) return '—';
		switch (metric.format) {
			case 'percent':
				return formatPercent(value, 1);
			case 'bytes':
				return formatBytes(value);
			case 'mbps':
				return `${formatNumber(value, 1)} Mbps`;
			case 'bps':
				return value >= 1e6
					? `${formatNumber(value / 1e6, 1)} Mbps`
					: `${formatNumber(value / 1e3, 1)} kbps`;
			case 'celsius':
				return `${formatNumber(value, 1)} °C`;
			case 'money':
				return `$${formatNumber(value, 2)}`;
			case 'rpm':
				return `${formatNumber(value, 0)} rpm`;
			default:
				return formatNumber(value);
		}
	}

	onMount(() => {
		void load(24);
		const timer = setInterval(() => {
			if (!document.hidden) void load(hours);
		}, 300_000);
		return () => clearInterval(timer);
	});
</script>

{#if metrics.length > 0}
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex items-start gap-3">
				<span
					class="inline-flex h-9 w-9 items-center justify-center rounded-[11px] bg-surface-2 text-ink-2"
				>
					<ChartNoAxesColumn size={17} aria-hidden="true" />
				</span>
				<div>
					<h2 class="text-[17px] font-semibold text-ink">Histórico</h2>
					<p class="mt-0.5 text-[12px] text-ink-3">
						Muestras cada 5 min · {samples.length} puntos{lastAt
							? ` · última ${formatTime(lastAt)}`
							: ''}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-1 rounded-[10px] border border-line bg-surface-2/60 p-1">
				{#each ranges as range (range.hours)}
					<button
						type="button"
						class="rounded-[7px] px-2.5 py-1 text-[12px] font-medium transition-colors {hours ===
						range.hours
							? 'bg-surface text-ink shadow-sm'
							: 'text-ink-3 hover:text-ink'}"
						onclick={() => load(range.hours)}
					>
						{range.label}
					</button>
				{/each}
			</div>
		</div>

		{#if error}
			<div
				class="mt-4 flex items-center justify-between gap-3 rounded-[12px] bg-surface-2/60 px-3 py-2"
			>
				<p class="text-[12px] text-ink-2">{error}</p>
				<button
					type="button"
					class="inline-flex items-center gap-1 text-[12px] font-medium text-accent"
					onclick={() => load(hours)}
				>
					<RotateCw size={13} aria-hidden="true" /> Reintentar
				</button>
			</div>
		{:else if samples.length === 0 && !loading}
			<p class="mt-5 rounded-[12px] bg-surface-2/60 px-3 py-6 text-center text-[13px] text-ink-2">
				Recopilando histórico. La primera muestra tarda unos segundos y las gráficas se completan
				cada 5 minutos.
			</p>
		{:else}
			<div class="mt-5 grid gap-x-6 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
				{#each metrics as metric (metric.key)}
					{@const values = samples
						.map((sample) => sample.metrics[metric.key])
						.filter(
							(value): value is number => typeof value === 'number' && Number.isFinite(value)
						)}
					{@const current = values.length > 0 ? values[values.length - 1] : undefined}
					<div class="min-w-0">
						<div class="flex items-baseline justify-between gap-2">
							<p class="truncate text-[12px] font-medium text-ink-2">{metric.label}</p>
							<p class="tabular shrink-0 text-[13px] font-semibold text-ink">
								{formatValue(current, metric)}
							</p>
						</div>
						<div class="mt-1.5">
							<Sparkline {values} color={metric.color} />
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
