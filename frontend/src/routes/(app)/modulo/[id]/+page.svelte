<script lang="ts">
	import { ArrowLeft, CircleCheck, RotateCw } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { api } from '#lib/api';
	import Meter from '#lib/components/Meter.svelte';
	import ModuleIcon from '#lib/components/ModuleIcon.svelte';
	import OfflineBanner from '#lib/components/OfflineBanner.svelte';
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
	{:else}
		<div class="rounded-brand-lg border border-line bg-surface p-6">
			<p class="text-[14px] text-ink-2">
				Este módulo aún no tiene una vista específica. Los datos en bruto están disponibles en la
				API.
			</p>
		</div>
	{/if}
</section>
