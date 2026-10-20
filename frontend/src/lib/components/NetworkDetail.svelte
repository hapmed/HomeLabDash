<script lang="ts">
	import { ArrowDown, ArrowUp, Cable, Wifi } from '@lucide/svelte';

	import { formatBytes, formatNumber } from '#lib/format';
	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const interfaces = $derived(asArray(detail.interfaces).map(asObject));
	const totalRx = $derived(asNumber(detail.total_rx_bps, 0));
	const totalTx = $derived(asNumber(detail.total_tx_bps, 0));
	const errorDelta = $derived(
		asNumber(detail.rx_error_delta, 0) +
			asNumber(detail.tx_error_delta, 0) +
			asNumber(detail.rx_dropped_delta, 0) +
			asNumber(detail.tx_dropped_delta, 0)
	);
	const up = $derived(interfaces.filter((item) => item.up === true).length);
	const sampledAt = $derived(asString(detail.sampled_at, '—'));

	function rate(bps: unknown): string {
		const value = asOptionalNumber(bps);
		if (value === null) return '—';
		if (value >= 1_000_000) return `${formatNumber(value / 1_000_000, 2)} Mbps`;
		if (value >= 1_000) return `${formatNumber(value / 1_000, 1)} kbps`;
		return `${formatNumber(value, 0)} bps`;
	}

	function stateLabel(item: Record<string, unknown>): string {
		if (item.up === true) return 'Activa';
		return asString(item.state, 'down') === 'down' ? 'Desconectada' : asString(item.state, '—');
	}
</script>

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile label="Bajada" value={rate(totalRx)} hint="suma de interfaces activas" />
	<StatTile label="Subida" value={rate(totalTx)} hint="suma de interfaces activas" />
	<StatTile label="Interfaces" value={`${up}/${interfaces.length}`} hint="activas / visibles" />
	<StatTile
		label="Errores"
		value={formatNumber(errorDelta, 0)}
		hint="errores y descartes desde la última muestra"
	/>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-start justify-between gap-2">
		<div>
			<h2 class="text-[17px] font-semibold text-ink">Interfaces</h2>
			<p class="mt-1 text-[12px] text-ink-3">
				Muestreo cada 5 s · última lectura {sampledAt && sampledAt !== '—'
					? sampledAt.slice(11, 19)
					: '—'}
			</p>
		</div>
	</div>

	{#if interfaces.length === 0}
		<p class="mt-4 rounded-brand bg-surface-2/50 px-4 py-6 text-center text-[13px] text-ink-2">
			No se detectaron interfaces de red en el host.
		</p>
	{:else}
		<div class="mt-4 grid gap-3 lg:grid-cols-2">
			{#each interfaces as item (asString(item.name))}
				{@const isUp = item.up === true}
				{@const wifi = asString(item.type) === 'wifi'}
				<div class="rounded-brand border border-line bg-surface-2/35 p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="flex min-w-0 items-center gap-2.5">
							<span
								class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-[11px] bg-surface text-ink-2"
							>
								{#if wifi}
									<Wifi size={17} aria-hidden="true" />
								{:else}
									<Cable size={17} aria-hidden="true" />
								{/if}
							</span>
							<div class="min-w-0">
								<p class="truncate text-[14px] font-semibold text-ink">{asString(item.name)}</p>
								<p class="mt-0.5 text-[12px] text-ink-3">
									{asString(item.mac, 'sin MAC')} · MTU {asNumber(item.mtu, 0)}
								</p>
							</div>
						</div>
						<span
							class="inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium {isUp
								? 'bg-success/15 text-success'
								: 'bg-danger/10 text-danger'}"
						>
							<span class="h-1.5 w-1.5 rounded-full {isUp ? 'bg-success' : 'bg-danger'}"></span>
							{stateLabel(item)}
						</span>
					</div>

					<div class="mt-4 grid grid-cols-2 gap-2">
						<div class="rounded-[12px] bg-surface px-3 py-2">
							<p class="flex items-center gap-1 text-[11px] font-medium text-ink-3">
								<ArrowDown size={12} aria-hidden="true" /> Recepción
							</p>
							<p class="tabular mt-1 text-[14px] font-semibold text-ink">{rate(item.rx_bps)}</p>
							<p class="mt-0.5 text-[11px] text-ink-3">
								{formatBytes(asOptionalNumber(item.rx_bytes))} total
							</p>
						</div>
						<div class="rounded-[12px] bg-surface px-3 py-2">
							<p class="flex items-center gap-1 text-[11px] font-medium text-ink-3">
								<ArrowUp size={12} aria-hidden="true" /> Envío
							</p>
							<p class="tabular mt-1 text-[14px] font-semibold text-ink">{rate(item.tx_bps)}</p>
							<p class="mt-0.5 text-[11px] text-ink-3">
								{formatBytes(asOptionalNumber(item.tx_bytes))} total
							</p>
						</div>
					</div>

					<div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-ink-3">
						<span>Velocidad {item.speed_mbps ? `${asNumber(item.speed_mbps)} Mbps` : '—'}</span>
						<span>Errores RX/TX {asNumber(item.rx_errors)}/{asNumber(item.tx_errors)}</span>
						<span>Descartes RX/TX {asNumber(item.rx_dropped)}/{asNumber(item.tx_dropped)}</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
