<script lang="ts">
	import { ArrowLeft, CircleCheck, RotateCw, WifiOff } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { api } from '#lib/api';
	import Meter from '#lib/components/Meter.svelte';
	import ModuleIcon from '#lib/components/ModuleIcon.svelte';
	import OfflineBanner from '#lib/components/OfflineBanner.svelte';
	import SpeedChart from '#lib/components/SpeedChart.svelte';
	import StatTile from '#lib/components/StatTile.svelte';
	import StatusBadge from '#lib/components/StatusBadge.svelte';
	import {
		asArray,
		asNumber,
		asObject,
		asOptionalNumber,
		asStatus,
		asString,
		usageTone
	} from '#lib/detail';
	import {
		formatBytes,
		formatDateTime,
		formatNumber,
		formatPercent,
		formatTime,
		formatUptime
	} from '#lib/format';
	import { parseHistory } from '#lib/internet';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let module = $state(data.module);
	let updatedAt = $state(new Date(data.updatedAt));
	let refreshing = $state(false);

	const detail = $derived(asObject(module.detail));
	const cores = $derived(asArray(detail.cores).map((core) => asNumber(asObject(core).percent)));
	const mounts = $derived(asArray(detail.mounts).map(asObject));
	const alerts = $derived(asArray(detail.alerts).map(asObject));
	const load = $derived(asObject(detail.load));
	const swap = $derived(asObject(detail.swap));
	const pressure = $derived(asObject(detail.pressure));
	const io = $derived(asObject(detail.io));
	const model = $derived(asString(detail.model, 'CPU'));
	const pressureEntries = $derived(Object.entries(pressure));

	const internetSamples = $derived(parseHistory(detail.history));
	const internetOnline = $derived(detail.online === true);
	const internetIp = $derived(asString(detail.public_ip));
	const internetIpVersion = $derived(asString(detail.ip_version, ''));
	const internetCountry = $derived(asString(detail.country, ''));
	const internetIsp = $derived(asString(detail.isp));
	const internetLocation = $derived(
		[asString(detail.city, ''), asString(detail.region, ''), internetCountry]
			.filter(Boolean)
			.join(', ') || '—'
	);
	const internetDownload = $derived(asOptionalNumber(detail.download_mbps));
	const internetUpload = $derived(asOptionalNumber(detail.upload_mbps));
	const internetLatency = $derived(asOptionalNumber(detail.latency_ms));
	const internetJitter = $derived(asOptionalNumber(detail.jitter_ms));
	const internetLastTest = $derived(asString(detail.last_test_at, ''));
	const internetNextTest = $derived(asString(detail.next_test_at, ''));
	const internetInterval = $derived(asNumber(detail.test_interval_minutes, 60));
	const internetPreviousIp = $derived(asString(detail.previous_ip, ''));
	const internetError = $derived(asString(detail.last_error, ''));
	const internetConsumption = $derived(
		asNumber(detail.download_test_bytes, 0) + asNumber(detail.upload_test_bytes, 0)
	);

	const deviceList = $derived(
		asArray(detail.devices)
			.map(asObject)
			.sort((left, right) => {
				const onlineDiff = Number(right.online === true) - Number(left.online === true);
				if (onlineDiff !== 0) return onlineDiff;
				const bytesDiff =
					(asOptionalNumber(right.bytes_cycle) ?? asOptionalNumber(right.bytes) ?? 0) -
					(asOptionalNumber(left.bytes_cycle) ?? asOptionalNumber(left.bytes) ?? 0);
				if (bytesDiff !== 0) return bytesDiff;
				return asString(left.name, '').localeCompare(asString(right.name, ''), 'es');
			})
	);
	const deviceCounts = $derived(asObject(detail.counts));
	const deviceOnline = $derived(asNumber(deviceCounts.online, 0));
	const deviceTotal = $derived(asNumber(deviceCounts.total, 0));
	const deviceNetworkName = $derived(asString(detail.network_name, 'Red local'));
	const deviceCidr = $derived(asString(detail.cidr));
	const deviceGateway = $derived(asString(detail.gateway));
	const deviceInterface = $derived(asString(detail.interface, '—'));
	const deviceSource = $derived(asString(detail.source, 'arp'));
	const deviceConsumptionAvailable = $derived(detail.consumption_available === true);
	const deviceTopConsumer = $derived(asObject(detail.top_consumer));
	const deviceTopConsumerName = $derived(asString(deviceTopConsumer.name, ''));
	const deviceWarning = $derived(asString(detail.warning, ''));
	const deviceLastScan = $derived(asString(detail.last_scan_at, ''));
	const deviceScanInterval = $derived(asNumber(detail.scan_interval_seconds, 60));
	const deviceConsumptionNote = $derived(asString(detail.consumption_note, ''));
	const deviceRouter = $derived(asObject(detail.router));
	const billing = $derived(asObject(detail.billing));
	const billingCurrent = $derived(asObject(billing.current));
	const billingHistory = $derived(asArray(billing.history).map(asObject));
	const billingCycleStart = $derived(asString(billingCurrent.cycle_start, '—'));
	const billingCycleEnd = $derived(asString(billingCurrent.cycle_end, '—'));
	const billingCycleDay = $derived(asNumber(billing.cycle_day, 10));
	const billingTimezone = $derived(asString(billing.timezone, 'America/Monterrey'));
	const billingDailyDays = $derived(asNumber(billing.daily_history_days, 62));
	const billingWanBytes = $derived(asOptionalNumber(billingCurrent.wan_bytes));
	const billingWanAvailable = $derived(billingCurrent.wan_available === true);
	const billingDeviceBytes = $derived(asOptionalNumber(billingCurrent.device_bytes) ?? 0);
	const billingTop = $derived(asObject(billingCurrent.top_device));
	const billingTopName = $derived(asString(billingTop.name, ''));
	const billingTopBytes = $derived(asOptionalNumber(billingTop.bytes));
	const daily = $derived(asObject(billing.daily));
	const dailyCurrent = $derived(asObject(daily.current));
	const dailyHistory = $derived(asArray(daily.history).map(asObject));
	const dailyDate = $derived(asString(dailyCurrent.date, '—'));
	const dailyWanBytes = $derived(asOptionalNumber(dailyCurrent.wan_bytes));
	const dailyWanAvailable = $derived(dailyCurrent.wan_available === true);
	const dailyDeviceBytes = $derived(asOptionalNumber(dailyCurrent.device_bytes) ?? 0);
	const dailyTop = $derived(asObject(dailyCurrent.top_device));
	const dailyTopName = $derived(asString(dailyTop.name, ''));
	const dailyTopBytes = $derived(asOptionalNumber(dailyTop.bytes));

	function deviceTypeLabel(type: unknown): string {
		const value = asString(type, 'device');
		if (value === 'router') return 'Router';
		if (value === 'server') return 'Servidor';
		return 'Cliente';
	}

	async function refresh() {
		if (typeof document !== 'undefined' && document.hidden) return;
		refreshing = true;
		try {
			module = await api.module(module.id);
			updatedAt = new Date();
		} catch {
			module = { ...module, available: false, error: 'sin conexión con el agente' };
		} finally {
			refreshing = false;
		}
	}

	onMount(() => {
		const timer = setInterval(refresh, 5000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<title>{module.name} · HomeLabDash</title>
</svelte:head>

<section class="flex flex-col gap-6">
	<a
		href="/"
		class="inline-flex w-fit items-center gap-1.5 text-[13px] font-medium text-ink-2 no-underline transition-colors hover:text-ink"
	>
		<ArrowLeft size={15} aria-hidden="true" />
		Panel
	</a>

	<div class="flex flex-wrap items-start justify-between gap-4">
		<div class="flex items-start gap-3">
			<span
				class="inline-flex h-12 w-12 items-center justify-center rounded-[14px] bg-surface-2 text-ink-2"
			>
				<ModuleIcon name={module.icon} size={24} />
			</span>
			<div>
				<div class="flex flex-wrap items-center gap-2.5">
					<h1 class="text-[30px] leading-tight font-semibold tracking-tight text-ink">
						{module.name}
					</h1>
					<StatusBadge status={module.status} />
				</div>
				<p class="mt-1 text-[14px] text-ink-2">{module.description}</p>
				<p class="mt-1 text-[12px] text-ink-3">
					Actualizado a las {formatTime(updatedAt)} · se refresca cada 5 s
				</p>
			</div>
		</div>

		<button
			type="button"
			class="inline-flex min-h-10 items-center gap-2 rounded-[12px] border border-line bg-surface px-3.5 text-[13px] font-medium text-ink-2 transition-colors hover:text-ink disabled:opacity-60"
			onclick={refresh}
			disabled={refreshing}
		>
			<RotateCw size={15} class={refreshing ? 'animate-spin' : ''} aria-hidden="true" />
			Actualizar
		</button>
	</div>

	{#if !module.available}
		<OfflineBanner
			message="El agente no responde ahora mismo. Se muestra el último estado conocido; los valores pueden estar desactualizados."
		/>
	{/if}

	{#if module.id === 'overview'}
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatTile label="Uptime" value={asString(detail.uptime_human)} hint="desde el arranque" />
			<StatTile
				label="Carga 1m"
				value={formatNumber(asOptionalNumber(load['1m']))}
				hint={`5m ${formatNumber(asOptionalNumber(load['5m']))} · 15m ${formatNumber(
					asOptionalNumber(load['15m'])
				)}`}
			/>
			<StatTile
				label="CPU"
				value={formatPercent(asOptionalNumber(detail.cpu_percent), 1)}
				hint="uso actual"
			/>
			<StatTile
				label="RAM"
				value={formatPercent(asOptionalNumber(detail.memory_percent), 1)}
				hint="memoria en uso"
			/>
		</div>

		<div class="grid gap-4 lg:grid-cols-2">
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Host</h2>
				<dl class="mt-4 grid gap-x-6 gap-y-3 text-[13px] sm:grid-cols-[140px_1fr]">
					<dt class="text-ink-3">Nombre</dt>
					<dd class="font-medium text-ink">{asString(detail.hostname)}</dd>
					<dt class="text-ink-3">Sistema</dt>
					<dd class="font-medium text-ink">{asString(detail.os)}</dd>
					<dt class="text-ink-3">Kernel</dt>
					<dd class="break-all font-medium text-ink">{asString(detail.kernel)}</dd>
					<dt class="text-ink-3">Arranque</dt>
					<dd class="font-medium text-ink">{formatDateTime(asString(detail.boot_time, ''))}</dd>
					<dt class="text-ink-3">Disco raíz</dt>
					<dd class="font-medium text-ink">
						{formatPercent(asOptionalNumber(detail.disk_percent), 1)}
					</dd>
				</dl>
			</div>

			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Alertas</h2>
				{#if alerts.length === 0}
					<p class="mt-4 inline-flex items-center gap-2 text-[13px] text-ink-2">
						<CircleCheck size={16} class="text-success" aria-hidden="true" />
						Sin alertas activas
					</p>
				{:else}
					<ul class="mt-4 flex flex-col gap-2">
						{#each alerts as alert}
							<li
								class="flex items-start gap-2 rounded-brand border border-line bg-surface-2/50 px-3 py-2 text-[13px]"
							>
								<span
									class="mt-1.5 h-2 w-2 shrink-0 rounded-full {alert.severity === 'critical'
										? 'bg-danger'
										: 'bg-warning'}"
									aria-hidden="true"
								></span>
								<span class="text-ink">{asString(alert.message)}</span>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>
	{:else if module.id === 'cpu'}
		<div class="grid gap-4 lg:grid-cols-[1.15fr_1fr]">
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Uso global</h2>
				<div class="mt-5">
					<Meter
						label="CPU"
						value={asNumber(detail.percent)}
						status={asStatus(module.status)}
						detail={model}
					/>
				</div>
				<div class="mt-5 grid gap-4 sm:grid-cols-3">
					<StatTile
						label="Núcleos"
						value={`${asNumber(detail.logical_cores)} hilos`}
						hint={`${asNumber(detail.physical_cores)} físicos`}
					/>
					<StatTile
						label="Frecuencia"
						value={detail.frequency_mhz ? `${asNumber(detail.frequency_mhz)} MHz` : '—'}
						hint={detail.frequency_max_mhz
							? `máx. ${asNumber(detail.frequency_max_mhz)} MHz`
							: null}
					/>
					<StatTile
						label="Carga 1m"
						value={formatNumber(asOptionalNumber(load['1m']))}
						hint={`por núcleo ${formatNumber(asOptionalNumber(detail.load_per_core))}`}
					/>
				</div>
			</div>

			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Por núcleo</h2>
				<div class="mt-4 grid gap-3 sm:grid-cols-2">
					{#each cores as percent, index}
						<div>
							<div class="flex items-baseline justify-between text-[12px]">
								<span class="text-ink-2">Núcleo {index}</span>
								<span class="tabular font-medium text-ink">{formatPercent(percent, 0)}</span>
							</div>
							<div
								class="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2"
								aria-hidden="true"
							>
								<div
									class="h-full rounded-full {percent >= 90
										? 'bg-danger'
										: percent >= 75
											? 'bg-warning'
											: 'bg-success'}"
									style:width={`${Math.max(0, Math.min(100, percent))}%`}
								></div>
							</div>
						</div>
					{/each}
				</div>
				<dl class="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4 text-[12px]">
					<div>
						<dt class="text-ink-3">Carga 1m</dt>
						<dd class="tabular font-semibold text-ink">
							{formatNumber(asOptionalNumber(load['1m']))}
						</dd>
					</div>
					<div>
						<dt class="text-ink-3">Carga 5m</dt>
						<dd class="tabular font-semibold text-ink">
							{formatNumber(asOptionalNumber(load['5m']))}
						</dd>
					</div>
					<div>
						<dt class="text-ink-3">Carga 15m</dt>
						<dd class="tabular font-semibold text-ink">
							{formatNumber(asOptionalNumber(load['15m']))}
						</dd>
					</div>
				</dl>
			</div>
		</div>
	{:else if module.id === 'memory'}
		<div class="grid gap-4 lg:grid-cols-2">
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Memoria</h2>
				<div class="mt-5 flex flex-col gap-5">
					<Meter
						label="RAM"
						value={asNumber(detail.percent)}
						status={usageTone(asNumber(detail.percent))}
						detail={`${formatBytes(asOptionalNumber(detail.used_bytes))} de ${formatBytes(
							asOptionalNumber(detail.total_bytes)
						)}`}
					/>
					<Meter
						label="Swap"
						value={asNumber(swap.percent)}
						status={usageTone(asNumber(swap.percent))}
						detail={`${formatBytes(asOptionalNumber(swap.used_bytes))} de ${formatBytes(
							asOptionalNumber(swap.total_bytes)
						)}`}
					/>
				</div>
			</div>

			<div class="grid gap-4 sm:grid-cols-2">
				<StatTile label="Total" value={formatBytes(asOptionalNumber(detail.total_bytes))} />
				<StatTile label="En uso" value={formatBytes(asOptionalNumber(detail.used_bytes))} />
				<StatTile
					label="Disponible"
					value={formatBytes(asOptionalNumber(detail.available_bytes))}
				/>
				<StatTile label="Caché" value={formatBytes(asOptionalNumber(detail.cached_bytes))} />
			</div>
		</div>

		{#if pressureEntries.length > 0}
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Presión de memoria</h2>
				<div class="mt-4 grid gap-3 sm:grid-cols-2">
					{#each pressureEntries as [kind, value]}
						<StatTile
							label={kind === 'some' ? 'Alguna tarea' : 'Todas las tareas'}
							value={`${formatNumber(asNumber(value))}%`}
							hint="media 10 s"
						/>
					{/each}
				</div>
			</div>
		{/if}
	{:else if module.id === 'storage'}
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatTile
				label="Disco raíz"
				value={formatPercent(asOptionalNumber(detail.percent), 1)}
				hint="en uso"
			/>
			<StatTile label="Montajes" value={mounts.length} hint="sistemas de archivos" />
			<StatTile
				label="Leído"
				value={formatBytes(asOptionalNumber(io.read_bytes))}
				hint="desde el arranque"
			/>
			<StatTile
				label="Escrito"
				value={formatBytes(asOptionalNumber(io.write_bytes))}
				hint="desde el arranque"
			/>
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Puntos de montaje</h2>
			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[620px] border-collapse text-[13px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Montaje</th>
							<th class="pb-2 pr-4 font-medium">Dispositivo</th>
							<th class="pb-2 pr-4 font-medium">Tipo</th>
							<th class="pb-2 pr-4 font-medium">Uso</th>
							<th class="pb-2 font-medium">Libre</th>
						</tr>
					</thead>
					<tbody>
						{#each mounts as mount}
							{@const percent = asNumber(mount.percent)}
							<tr class="border-b border-line/60 last:border-0">
								<td class="py-2.5 pr-4 font-medium text-ink">{asString(mount.mountpoint)}</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(mount.device)}</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(mount.fstype)}</td>
								<td class="py-2.5 pr-4">
									<div class="flex items-center gap-2">
										<div
											class="h-1.5 w-24 overflow-hidden rounded-full bg-surface-2"
											aria-hidden="true"
										>
											<div
												class="h-full rounded-full {percent >= 95
													? 'bg-danger'
													: percent >= 85
														? 'bg-warning'
														: 'bg-success'}"
												style:width={`${Math.max(0, Math.min(100, percent))}%`}
											></div>
										</div>
										<span class="tabular text-ink">{formatPercent(percent, 1)}</span>
									</div>
								</td>
								<td class="tabular py-2.5 text-ink-2"
									>{formatBytes(asOptionalNumber(mount.free_bytes))}</td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{:else if module.id === 'internet'}
		{#if !internetOnline}
			<div
				role="status"
				class="flex items-start gap-3 rounded-brand-lg border border-danger/30 bg-danger/10 px-4 py-3 text-[14px] text-ink"
			>
				<WifiOff size={18} class="mt-0.5 shrink-0 text-danger" aria-hidden="true" />
				<p>Sin conexión a Internet. Se muestra el último estado conocido.</p>
			</div>
		{/if}

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatTile
				label="Bajada"
				value={internetDownload !== null ? `${formatNumber(internetDownload, 1)} Mbps` : '—'}
				hint="última prueba de velocidad"
			/>
			<StatTile
				label="Subida"
				value={internetUpload !== null ? `${formatNumber(internetUpload, 1)} Mbps` : '—'}
				hint="última prueba de velocidad"
			/>
			<StatTile
				label="Latencia"
				value={internetLatency !== null ? `${formatNumber(internetLatency, 1)} ms` : '—'}
				hint={internetJitter !== null ? `jitter ${formatNumber(internetJitter, 1)} ms` : null}
			/>
			<StatTile
				label="IP pública"
				value={internetIp}
				hint={[internetIpVersion, internetCountry].filter(Boolean).join(' · ') || null}
			/>
		</div>

		<div class="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 class="text-[17px] font-semibold text-ink">Histórico de velocidad</h2>
					<span class="text-[12px] text-ink-3">
						{internetSamples.length} pruebas · cada {internetInterval} min
					</span>
				</div>
				<div class="mt-4">
					<SpeedChart history={detail.history} />
				</div>
			</div>

			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Conexión</h2>
				<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[128px_1fr]">
					<dt class="text-ink-3">Estado</dt>
					<dd class="font-medium {internetOnline ? 'text-success' : 'text-danger'}">
						{internetOnline ? 'En línea' : 'Sin conexión'}
					</dd>
					<dt class="text-ink-3">Proveedor</dt>
					<dd class="font-medium text-ink">{internetIsp}</dd>
					<dt class="text-ink-3">Ubicación</dt>
					<dd class="font-medium text-ink">{internetLocation}</dd>
					<dt class="text-ink-3">Edge</dt>
					<dd class="font-medium text-ink">
						{[
							asString(detail.colo, ''),
							asString(detail.http_version, ''),
							asString(detail.tls, '')
						]
							.filter(Boolean)
							.join(' · ') || '—'}
					</dd>
					<dt class="text-ink-3">Última prueba</dt>
					<dd class="font-medium text-ink">{formatDateTime(internetLastTest)}</dd>
					<dt class="text-ink-3">Próxima</dt>
					<dd class="font-medium text-ink">{formatDateTime(internetNextTest)}</dd>
					<dt class="text-ink-3">Consumo por prueba</dt>
					<dd class="font-medium text-ink">≈ {formatBytes(internetConsumption)}</dd>
				</dl>

				{#if internetPreviousIp && internetPreviousIp !== '—' && internetPreviousIp !== internetIp}
					<p
						class="mt-4 rounded-brand border border-warning/30 bg-warning/10 px-3 py-2 text-[12px] text-ink"
					>
						La IP pública cambió: antes {internetPreviousIp}, ahora {internetIp}.
					</p>
				{/if}
			</div>
		</div>

		{#if internetError}
			<p
				class="rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[13px] text-ink"
			>
				Último error de medición: {internetError}
			</p>
		{/if}

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Últimas pruebas</h2>
			{#if internetSamples.length === 0}
				<p class="mt-4 text-[13px] text-ink-3">
					Todavía no hay pruebas registradas. La primera se ejecuta al arrancar el agente.
				</p>
			{:else}
				<div class="mt-4 overflow-x-auto">
					<table class="w-full min-w-[520px] border-collapse text-[13px]">
						<thead>
							<tr
								class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
							>
								<th class="pb-2 pr-4 font-medium">Fecha</th>
								<th class="pb-2 pr-4 font-medium">Bajada</th>
								<th class="pb-2 pr-4 font-medium">Subida</th>
								<th class="pb-2 font-medium">Latencia</th>
							</tr>
						</thead>
						<tbody>
							{#each [...internetSamples].slice(-10).reverse() as sample (sample.at)}
								<tr class="border-b border-line/60 last:border-0">
									<td class="py-2.5 pr-4 text-ink-2">{formatDateTime(sample.at)}</td>
									<td class="tabular py-2.5 pr-4 font-medium text-ink">
										{formatNumber(sample.download_mbps, 1)} Mbps
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">
										{formatNumber(sample.upload_mbps, 1)} Mbps
									</td>
									<td class="tabular py-2.5 text-ink-2">
										{sample.latency_ms !== null ? `${formatNumber(sample.latency_ms, 1)} ms` : '—'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	{:else if module.id === 'devices'}
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatTile label="En línea" value={deviceOnline} hint={`de ${deviceTotal} conocidos`} />
			<StatTile
				label="Consumo hoy"
				value={dailyWanAvailable ? formatBytes(dailyWanBytes) : formatBytes(dailyDeviceBytes)}
				hint={dailyWanAvailable ? 'WAN real · hoy' : 'estimado · hoy'}
			/>
			<StatTile
				label="Consumo del ciclo"
				value={billingWanAvailable ? formatBytes(billingWanBytes) : formatBytes(billingDeviceBytes)}
				hint={billingWanAvailable ? 'WAN real · ciclo' : 'estimado · ciclo'}
			/>
			<StatTile
				label="Corte del ciclo"
				value={billingCycleEnd}
				hint={`día ${billingCycleDay} · ${billingTimezone}`}
			/>
		</div>

		{#if deviceWarning}
			<div
				role="status"
				class="rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[13px] text-ink"
			>
				{deviceWarning}
			</div>
		{/if}

		<div class="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Resumen de la red</h2>
				<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[150px_1fr]">
					<dt class="text-ink-3">Nombre</dt>
					<dd class="font-medium text-ink">{deviceNetworkName}</dd>
					<dt class="text-ink-3">Rango</dt>
					<dd class="font-medium text-ink">{deviceCidr}</dd>
					<dt class="text-ink-3">Puerta de enlace</dt>
					<dd class="font-medium text-ink">{deviceGateway}</dd>
					<dt class="text-ink-3">Interfaz</dt>
					<dd class="font-medium text-ink">{deviceInterface}</dd>
					<dt class="text-ink-3">Fuente</dt>
					<dd class="font-medium text-ink">
						{deviceSource === 'router' ? 'Router' : 'ARP del host'}
					</dd>
					<dt class="text-ink-3">Ciclo actual</dt>
					<dd class="font-medium text-ink">{billingCycleStart} → {billingCycleEnd}</dd>
					<dt class="text-ink-3">Hoy</dt>
					<dd class="font-medium text-ink">
						{dailyDate} ·
						{dailyWanAvailable ? formatBytes(dailyWanBytes) : formatBytes(dailyDeviceBytes)}
					</dd>
					<dt class="text-ink-3">Corte diario</dt>
					<dd class="font-medium text-ink">00:00 · {billingTimezone}</dd>
					<dt class="text-ink-3">Internet (WAN)</dt>
					<dd class="font-medium text-ink">
						{billingWanAvailable ? formatBytes(billingWanBytes) : '—'}
					</dd>
					<dt class="text-ink-3">Dispositivos</dt>
					<dd class="font-medium text-ink">{formatBytes(billingDeviceBytes)} estimados</dd>
					<dt class="text-ink-3">Último escaneo</dt>
					<dd class="font-medium text-ink">
						{formatTime(deviceLastScan)} · cada {deviceScanInterval} s
					</dd>
					<dt class="text-ink-3">Consumo</dt>
					<dd class="font-medium text-ink">
						{deviceConsumptionAvailable ? 'Disponible (estimado)' : 'No disponible'}
					</dd>
					{#if deviceRouter.enabled}
						<dt class="text-ink-3">Router</dt>
						<dd class="font-medium text-ink">
							{asString(deviceRouter.model, 'Mercusys')}
							{#if asString(deviceRouter.ssid, '')}
								· {asString(deviceRouter.ssid)}
							{/if}
						</dd>
					{/if}
				</dl>
			</div>

			<div class="rounded-brand-lg border border-line bg-surface p-5">
				<h2 class="text-[17px] font-semibold text-ink">Mayor consumo</h2>
				{#if deviceTopConsumerName}
					<p class="mt-4 text-[20px] font-semibold text-ink">{deviceTopConsumerName}</p>
					<p class="mt-1 text-[13px] text-ink-2">
						{formatBytes(asOptionalNumber(deviceTopConsumer.bytes))} en este ciclo
						{#if asString(deviceTopConsumer.ip, '')}· {asString(deviceTopConsumer.ip)}{/if}
					</p>
					{#if deviceConsumptionNote}
						<p class="mt-2 text-[12px] text-ink-3">{deviceConsumptionNote}</p>
					{/if}
					{#if dailyTopName}
						<p class="mt-2 text-[13px] text-ink-2">
							Hoy: {dailyTopName} · {formatBytes(dailyTopBytes)}
						</p>
					{/if}
				{:else}
					<p class="mt-4 text-[13px] text-ink-2">Sin datos de consumo en este ciclo.</p>
					<p class="mt-1 text-[12px] text-ink-3">
						El consumo se calcula muestreando las tasas que publica el router. Aún no hay
						suficientes muestras o el router no está accesible.
					</p>
				{/if}
			</div>
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<div class="flex flex-wrap items-baseline justify-between gap-2">
				<h2 class="text-[17px] font-semibold text-ink">Dispositivos</h2>
				<span class="text-[12px] text-ink-3">
					{deviceOnline} en línea · {deviceTotal} conocidos
				</span>
			</div>

			{#if deviceList.length === 0}
				<p class="mt-4 text-[13px] text-ink-3">
					Todavía no se ha detectado ningún dispositivo. El primer escaneo tarda unos segundos.
				</p>
			{:else}
				<div class="mt-4 overflow-x-auto">
					<table class="w-full min-w-[1200px] border-collapse text-[13px]">
						<thead>
							<tr
								class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
							>
								<th class="pb-2 pr-4 font-medium">Estado</th>
								<th class="pb-2 pr-4 font-medium">Nombre</th>
								<th class="pb-2 pr-4 font-medium">IP</th>
								<th class="pb-2 pr-4 font-medium">MAC</th>
								<th class="pb-2 pr-4 font-medium">Conexión</th>
								<th class="pb-2 pr-4 font-medium">Fabricante</th>
								<th class="pb-2 pr-4 font-medium">Primera vez</th>
								<th class="pb-2 pr-4 font-medium">Última vez</th>
								<th class="pb-2 pr-4 font-medium">Tiempo en línea</th>
								<th class="pb-2 pr-4 font-medium">Tasa ↑ / ↓</th>
								<th class="pb-2 pr-4 font-medium">Consumo mes</th>
								<th class="pb-2 font-medium">Total</th>
							</tr>
						</thead>
						<tbody>
							{#each deviceList as device (device.mac)}
								{@const isOnline = device.online === true}
								{@const monthBytes = asOptionalNumber(device.bytes_cycle)}
								{@const totalBytes = asOptionalNumber(device.bytes)}
								<tr class="border-b border-line/60 last:border-0">
									<td class="py-2.5 pr-4 whitespace-nowrap">
										<span class="inline-flex items-center gap-1.5">
											<span
												class="h-2 w-2 rounded-full {isOnline ? 'bg-success' : 'bg-ink-3/50'}"
												aria-hidden="true"
											></span>
											<span class="text-ink-2">{isOnline ? 'En línea' : 'Ausente'}</span>
										</span>
									</td>
									<td class="py-2.5 pr-4">
										<span class="font-medium text-ink">{asString(device.name)}</span>
										<span class="ml-1 text-[11px] text-ink-3">· {deviceTypeLabel(device.type)}</span
										>
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">{asString(device.ip)}</td>
									<td class="py-2.5 pr-4 font-mono text-[11px] text-ink-3">
										{asString(device.mac)}
									</td>
									<td class="py-2.5 pr-4 text-ink-2">{asString(device.connection, '—')}</td>
									<td class="py-2.5 pr-4 text-ink-2">{asString(device.vendor)}</td>
									<td class="py-2.5 pr-4 text-ink-2">
										{formatDateTime(asString(device.first_seen, ''))}
									</td>
									<td class="py-2.5 pr-4 text-ink-2">
										{formatDateTime(asString(device.last_seen, ''))}
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">
										{formatUptime(asNumber(device.online_seconds, 0))}
									</td>
									<td class="tabular py-2.5 pr-4 text-[12px] text-ink-2">
										↑ {formatBytes(asNumber(device.rate_up_bps, 0))}/s · ↓ {formatBytes(
											asNumber(device.rate_down_bps, 0)
										)}/s
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">
										{monthBytes !== null ? formatBytes(monthBytes) : '—'}
									</td>
									<td class="tabular py-2.5 text-ink-3">
										{totalBytes !== null ? formatBytes(totalBytes) : '—'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}

			<p class="mt-3 text-[12px] leading-5 text-ink-3">
				Presencia obtenida de la tabla ARP del host y del router. «Primera vez» empieza a contar
				desde que se activó este monitor; el tiempo en línea se acumula entre escaneos.
				{#if deviceConsumptionNote}
					{deviceConsumptionNote}
				{/if}
			</p>
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<div class="flex flex-wrap items-baseline justify-between gap-2">
				<h2 class="text-[17px] font-semibold text-ink">Consumo diario</h2>
				<span class="text-[12px] text-ink-3">
					Hoy · corte 00:00 · últimos {Math.min(14, billingDailyDays)} días
				</span>
			</div>

			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[780px] border-collapse text-[13px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Día</th>
							<th class="pb-2 pr-4 font-medium">Internet (WAN)</th>
							<th class="pb-2 pr-4 font-medium">Dispositivos</th>
							<th class="pb-2 pr-4 font-medium">Mayor consumidor</th>
							<th class="pb-2 font-medium">Consumo</th>
						</tr>
					</thead>
					<tbody>
						<tr class="border-b border-line/60 bg-surface-2/40">
							<td class="py-2.5 pr-4 font-medium text-ink">
								{dailyDate}
								<span class="ml-1 rounded-full bg-accent/10 px-2 py-0.5 text-[11px] text-accent">
									En curso
								</span>
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{dailyWanAvailable ? formatBytes(dailyWanBytes) : '—'}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">{formatBytes(dailyDeviceBytes)}</td>
							<td class="py-2.5 pr-4 text-ink-2">{dailyTopName || '—'}</td>
							<td class="tabular py-2.5 text-ink-2">{formatBytes(dailyTopBytes)}</td>
						</tr>

						{#each dailyHistory.slice(0, 14) as day (day.date)}
							{@const dayTop = asObject(day.top_device)}
							{@const dayWan = asOptionalNumber(day.wan_bytes) ?? 0}
							<tr class="border-b border-line/60 last:border-0">
								<td class="py-2.5 pr-4 font-medium text-ink">{asString(day.date)}</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{dayWan > 0 ? formatBytes(dayWan) : '—'}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatBytes(asOptionalNumber(day.device_bytes))}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(dayTop.name, '—')}</td>
								<td class="tabular py-2.5 text-ink-2">
									{formatBytes(asOptionalNumber(dayTop.bytes))}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			{#if dailyHistory.length === 0}
				<p class="mt-3 text-[12px] leading-5 text-ink-3">
					El primer día completo se archivará mañana a las 00:00. Hoy ya se está contabilizando.
				</p>
			{/if}
			<p class="mt-3 text-[12px] leading-5 text-ink-3">
				El consumo diario se reinicia a las 00:00 ({billingTimezone}). Internet usa los contadores
				WAN del router; los dispositivos son estimados e incluyen tráfico LAN. Se conservan
				{billingDailyDays} días.
			</p>
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<div class="flex flex-wrap items-baseline justify-between gap-2">
				<h2 class="text-[17px] font-semibold text-ink">Histórico mensual</h2>
				<span class="text-[12px] text-ink-3">
					Corte día {billingCycleDay} · {billingTimezone}
				</span>
			</div>

			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[780px] border-collapse text-[13px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Ciclo</th>
							<th class="pb-2 pr-4 font-medium">Internet (WAN)</th>
							<th class="pb-2 pr-4 font-medium">Dispositivos</th>
							<th class="pb-2 pr-4 font-medium">Mayor consumidor</th>
							<th class="pb-2 font-medium">Consumo</th>
						</tr>
					</thead>
					<tbody>
						<tr class="border-b border-line/60 bg-surface-2/40">
							<td class="py-2.5 pr-4 font-medium text-ink">
								{billingCycleStart} → {billingCycleEnd}
								<span class="ml-1 rounded-full bg-accent/10 px-2 py-0.5 text-[11px] text-accent">
									En curso
								</span>
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{billingWanAvailable ? formatBytes(billingWanBytes) : '—'}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatBytes(billingDeviceBytes)}
							</td>
							<td class="py-2.5 pr-4 text-ink-2">{billingTopName || '—'}</td>
							<td class="tabular py-2.5 text-ink-2">{formatBytes(billingTopBytes)}</td>
						</tr>

						{#each billingHistory as record (record.cycle_start)}
							{@const historyTop = asObject(record.top_device)}
							{@const historyWan = asOptionalNumber(record.wan_bytes) ?? 0}
							<tr class="border-b border-line/60 last:border-0">
								<td class="py-2.5 pr-4 font-medium text-ink">
									{asString(record.cycle_start)} → {asString(record.cycle_end)}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{historyWan > 0 ? formatBytes(historyWan) : '—'}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatBytes(asOptionalNumber(record.device_bytes))}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(historyTop.name, '—')}</td>
								<td class="tabular py-2.5 text-ink-2">
									{formatBytes(asOptionalNumber(historyTop.bytes))}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<p class="mt-3 text-[12px] leading-5 text-ink-3">
				El ciclo se reinicia el día {billingCycleDay} a las 00:00 ({billingTimezone}). El consumo de
				Internet sale de los contadores WAN del router; el de dispositivos es estimado e incluye
				tráfico LAN. El primer ciclo empieza al activar el monitor, así que puede estar incompleto.
			</p>
		</div>
	{:else}
		<div class="rounded-brand-lg border border-line bg-surface p-6">
			<p class="text-[14px] text-ink-2">
				Este módulo aún no tiene una vista específica. Los datos en bruto están disponibles en la
				API.
			</p>
		</div>
	{/if}
</section>
