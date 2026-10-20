<script lang="ts">
	import { Fan, Thermometer } from '@lucide/svelte';

	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatNumber } from '#lib/format';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const sensors = $derived(asArray(detail.sensors).map(asObject));
	const fans = $derived(asArray(detail.fans).map(asObject));
	const maxC = $derived(asOptionalNumber(detail.max_c));
	const warnC = $derived(asNumber(detail.warn_c, 75));
	const criticalC = $derived(asNumber(detail.critical_c, 85));

	function statusFor(temp: number): 'critical' | 'warn' | 'ok' {
		if (temp >= criticalC) return 'critical';
		if (temp >= warnC) return 'warn';
		return 'ok';
	}

	function barWidth(temp: number): string {
		const reference = criticalC > 0 ? criticalC : 100;
		return `${Math.max(2, Math.min(100, (temp / reference) * 100))}%`;
	}

	function tempColor(temp: number): string {
		const status = statusFor(temp);
		if (status === 'critical') return 'bg-danger';
		if (status === 'warn') return 'bg-warning';
		return 'bg-success';
	}
</script>

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile
		label="Máxima"
		value={maxC === null ? '—' : `${formatNumber(maxC, 1)} °C`}
		hint={maxC !== null
			? maxC >= criticalC
				? 'por encima del límite crítico'
				: maxC >= warnC
					? 'por encima del aviso'
					: 'dentro de rango'
			: 'sin sensores'}
	/>
	<StatTile label="Sensores" value={sensors.length} hint="zonas y chips detectados" />
	<StatTile label="Ventiladores" value={fans.length} hint="con lectura de RPM" />
	<StatTile
		label="Umbrales"
		value={`${formatNumber(warnC, 0)} / ${formatNumber(criticalC, 0)} °C`}
		hint="aviso / crítico"
	/>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<h2 class="text-[17px] font-semibold text-ink">Sensores</h2>
	{#if sensors.length === 0}
		<p class="mt-4 rounded-brand bg-surface-2/50 px-4 py-6 text-center text-[13px] text-ink-2">
			El host no expone sensores de temperatura legibles.
		</p>
	{:else}
		<div class="mt-4 grid gap-3 lg:grid-cols-2">
			{#each sensors as sensor (asString(sensor.id))}
				{@const temp = asNumber(sensor.temp_c, 0)}
				{@const status = statusFor(temp)}
				<div class="rounded-brand border border-line bg-surface-2/35 p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="flex min-w-0 items-center gap-2.5">
							<span
								class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-surface text-ink-2"
							>
								<Thermometer size={16} aria-hidden="true" />
							</span>
							<div class="min-w-0">
								<p class="truncate text-[13px] font-semibold text-ink">{asString(sensor.label)}</p>
								<p class="text-[11px] text-ink-3">
									{asString(sensor.chip)} · {asString(sensor.source)}
								</p>
							</div>
						</div>
						<p
							class="tabular shrink-0 text-[17px] font-semibold {status === 'critical'
								? 'text-danger'
								: status === 'warn'
									? 'text-warning'
									: 'text-ink'}"
						>
							{formatNumber(temp, 1)} °C
						</p>
					</div>
					<div class="mt-3 h-1.5 overflow-hidden rounded-full bg-surface">
						<div class="h-full rounded-full {tempColor(temp)}" style:width={barWidth(temp)}></div>
					</div>
					<p class="mt-2 text-[11px] text-ink-3">
						Máx {sensor.max_c ? `${formatNumber(asNumber(sensor.max_c), 1)} °C` : '—'} · Crítico {sensor.crit_c
							? `${formatNumber(asNumber(sensor.crit_c), 1)} °C`
							: '—'}
					</p>
				</div>
			{/each}
		</div>
	{/if}
</div>

{#if fans.length > 0}
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Ventiladores</h2>
		<div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
			{#each fans as fan (asString(fan.id))}
				<div
					class="flex items-center justify-between rounded-brand border border-line bg-surface-2/35 px-4 py-3"
				>
					<div class="flex items-center gap-2">
						<Fan size={16} class="text-ink-3" aria-hidden="true" />
						<span class="text-[13px] font-medium text-ink">{asString(fan.label)}</span>
					</div>
					<span class="tabular text-[13px] font-semibold text-ink">{asNumber(fan.rpm)} rpm</span>
				</div>
			{/each}
		</div>
	</div>
{/if}
