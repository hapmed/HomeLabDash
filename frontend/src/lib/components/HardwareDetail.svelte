<script lang="ts">
	import {
		BatteryCharging,
		HardDrive,
		Laptop,
		PlugZap,
		RefreshCw,
		ShieldAlert
	} from '@lucide/svelte';

	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatBytes, formatDateTime, formatNumber, formatPercent } from '#lib/format';
	import Meter from './Meter.svelte';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const host = $derived(asObject(detail.host));
	const disks = $derived(asArray(detail.disks).map(asObject));
	const battery = $derived(asObject(detail.battery));
	const hasBattery = $derived(detail.battery !== null && detail.battery !== undefined);
	const ac = $derived(asObject(detail.ac));
	const ups = $derived(asObject(detail.ups));
	const updates = $derived(asObject(detail.updates));
	const rootInodes = $derived(asOptionalNumber(detail.root_inodes_percent));
	const smartCount = $derived(
		disks.filter((disk) => asObject(disk.smart).available === true).length
	);
	const batteryPercent = $derived(asNumber(battery.percent, 0));
	const batteryStatus = $derived(batteryLabel(asString(battery.status, '—')));

	function batteryTone(percent: number): 'ok' | 'warn' | 'critical' {
		if (percent <= 10) return 'critical';
		if (percent <= 25) return 'warn';
		return 'ok';
	}

	function batteryLabel(status: string): string {
		const labels: Record<string, string> = {
			Full: 'Llena',
			Charging: 'Cargando',
			Discharging: 'Descargando',
			'Not charging': 'Sin carga',
			Unknown: 'Desconocido'
		};
		return labels[status] ?? status;
	}

	function smartStatusLabel(status: string): string {
		const labels: Record<string, string> = {
			passed: 'Correcto',
			failed: 'Fallido',
			unknown: 'Desconocido'
		};
		return labels[status] ?? status;
	}

	function smartLabel(disk: Record<string, unknown>): string {
		const smart = asObject(disk.smart);
		if (smart.available === true) return smartStatusLabel(asString(smart.status, 'unknown'));
		return 'No disponible';
	}
</script>

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile
		label="Batería"
		value={hasBattery ? formatPercent(batteryPercent, 0) : '—'}
		hint={hasBattery ? batteryStatus : 'sin batería detectada'}
	/>
	<StatTile
		label="Discos"
		value={disks.length}
		hint={smartCount > 0 ? `${smartCount} con SMART` : 'SMART no disponible'}
	/>
	<StatTile
		label="Inodos raíz"
		value={rootInodes === null ? '—' : formatPercent(rootInodes, 1)}
		hint="archivos e inodos del sistema"
	/>
	<StatTile
		label="Reinicio"
		value={updates.reboot_required === true ? 'Pendiente' : 'No'}
		hint="requiere reiniciar el host"
	/>
</div>

<div class="grid gap-4 lg:grid-cols-2">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-center gap-2.5">
			<Laptop size={18} class="text-ink-3" aria-hidden="true" />
			<h2 class="text-[17px] font-semibold text-ink">Equipo</h2>
		</div>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[100px_1fr]">
			<dt class="text-ink-3">Fabricante</dt>
			<dd class="font-medium text-ink">{asString(host.vendor)}</dd>
			<dt class="text-ink-3">Modelo</dt>
			<dd class="font-medium text-ink">{asString(host.model)}</dd>
			<dt class="text-ink-3">Placa</dt>
			<dd class="font-medium text-ink">{asString(host.board)}</dd>
			<dt class="text-ink-3">BIOS</dt>
			<dd class="font-medium text-ink">{asString(host.bios)}</dd>
			<dt class="text-ink-3">Serie</dt>
			<dd class="font-medium text-ink">{asString(host.serial)}</dd>
		</dl>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-center gap-2.5">
			<BatteryCharging size={18} class="text-ink-3" aria-hidden="true" />
			<h2 class="text-[17px] font-semibold text-ink">Energía</h2>
		</div>
		{#if hasBattery}
			<div class="mt-5">
				<Meter
					label="Batería"
					value={batteryPercent}
					status={batteryTone(batteryPercent)}
					detail={`${batteryStatus}${battery.voltage_v ? ` · ${formatNumber(asNumber(battery.voltage_v), 2)} V` : ''}`}
				/>
			</div>
			<dl
				class="mt-5 grid gap-x-4 gap-y-3 border-t border-line pt-4 text-[13px] sm:grid-cols-[140px_1fr]"
			>
				<dt class="text-ink-3">Modelo</dt>
				<dd class="font-medium text-ink">{asString(battery.model)}</dd>
				<dt class="text-ink-3">Salud</dt>
				<dd class="font-medium text-ink">
					{battery.health_percent ? formatPercent(asNumber(battery.health_percent), 1) : '—'}
				</dd>
				<dt class="text-ink-3">Ciclos</dt>
				<dd class="font-medium text-ink">{asNumber(battery.cycle_count, 0)}</dd>
				<dt class="text-ink-3">Consumo</dt>
				<dd class="font-medium text-ink">
					{battery.power_w ? `${formatNumber(asNumber(battery.power_w), 2)} W` : '—'}
				</dd>
				<dt class="text-ink-3">Autonomía</dt>
				<dd class="font-medium text-ink">
					{battery.runtime_minutes
						? `${formatNumber(asNumber(battery.runtime_minutes), 0)} min`
						: '—'}
				</dd>
				<dt class="text-ink-3">Corriente</dt>
				<dd class="font-medium text-ink">
					{ac.online === true ? 'Conectado a la red' : 'Batería'}
				</dd>
			</dl>
		{:else}
			<p class="mt-4 text-[13px] text-ink-2">No se detecta batería en el host.</p>
		{/if}
		<div
			class="mt-4 flex items-start gap-2 rounded-brand bg-surface-2/50 px-3 py-2.5 text-[12px] text-ink-2"
		>
			<PlugZap size={15} class="mt-0.5 shrink-0" aria-hidden="true" />
			<span>
				{ups.detected === true
					? 'SAI/UPS detectado por el sistema.'
					: 'No se detecta un SAI/UPS. La energía se lee de la batería del equipo.'}
			</span>
		</div>
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex items-center gap-2.5">
		<HardDrive size={18} class="text-ink-3" aria-hidden="true" />
		<h2 class="text-[17px] font-semibold text-ink">Discos y salud</h2>
	</div>
	{#if disks.length === 0}
		<p class="mt-4 rounded-brand bg-surface-2/50 px-4 py-6 text-center text-[13px] text-ink-2">
			No se detectaron discos en el host.
		</p>
	{:else}
		<div class="mt-4 grid gap-3">
			{#each disks as disk (asString(disk.name))}
				{@const smart = asObject(disk.smart)}
				{@const mounts = asArray(disk.mountpoints).map(asObject)}
				<div class="rounded-brand border border-line bg-surface-2/35 p-4">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<p class="text-[14px] font-semibold text-ink">
								{asString(disk.model, asString(disk.name))}
							</p>
							<p class="mt-0.5 text-[12px] text-ink-3">
								{asString(disk.name)} · {formatBytes(asOptionalNumber(disk.size_bytes))} · {disk.rotational
									? 'HDD'
									: 'SSD/NVMe'}
							</p>
						</div>
						<div class="flex flex-wrap items-center gap-2">
							{#if disk.temperature_c}
								<span class="rounded-full bg-surface px-2 py-1 text-[11px] font-medium text-ink-2">
									{formatNumber(asNumber(disk.temperature_c), 1)} °C
								</span>
							{/if}
							<span
								class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium {smart.available ===
								true
									? 'bg-success/15 text-success'
									: 'bg-warning/10 text-warning'}"
							>
								<ShieldAlert size={12} aria-hidden="true" />
								{smartLabel(disk)}
							</span>
						</div>
					</div>

					<dl class="mt-3 grid gap-x-4 gap-y-1.5 text-[12px] sm:grid-cols-2">
						<dt class="text-ink-3">Serie</dt>
						<dd class="font-medium text-ink">{asString(disk.serial)}</dd>
						<dt class="text-ink-3">Firmware</dt>
						<dd class="font-medium text-ink">{asString(disk.firmware)}</dd>
						<dt class="text-ink-3">Uso máximo</dt>
						<dd class="font-medium text-ink">
							{disk.usage_percent === null || disk.usage_percent === undefined
								? '—'
								: formatPercent(asNumber(disk.usage_percent), 1)}
						</dd>
						<dt class="text-ink-3">Inodos</dt>
						<dd class="font-medium text-ink">
							{disk.inodes_percent === null || disk.inodes_percent === undefined
								? '—'
								: formatPercent(asNumber(disk.inodes_percent), 1)}
						</dd>
					</dl>

					{#if smart.available === true}
						<div
							class="mt-3 grid gap-x-4 gap-y-1.5 rounded-[12px] bg-surface px-3 py-2.5 text-[12px] sm:grid-cols-2"
						>
							<span class="text-ink-3">Salud SMART</span>
							<span class="font-medium text-ink"
								>{smartStatusLabel(asString(smart.status, 'unknown'))}</span
							>
							<span class="text-ink-3">Horas encendido</span>
							<span class="font-medium text-ink">
								{smart.power_on_hours ? formatNumber(asNumber(smart.power_on_hours), 0) : '—'}
							</span>
							<span class="text-ink-3">Desgaste</span>
							<span class="font-medium text-ink">
								{smart.percentage_used === undefined || smart.percentage_used === null
									? '—'
									: formatPercent(asNumber(smart.percentage_used), 0)}
							</span>
							<span class="text-ink-3">Errores de medios</span>
							<span class="font-medium text-ink">{asNumber(smart.media_errors, 0)}</span>
						</div>
					{:else if smart.reason}
						<p class="mt-3 text-[11px] text-ink-3">{asString(smart.reason)}</p>
					{/if}

					{#if mounts.length > 0}
						<div class="mt-3 border-t border-line pt-3">
							{#each mounts as mount (asString(mount.mountpoint))}
								<div class="flex flex-wrap items-center justify-between gap-2 py-1 text-[12px]">
									<div>
										<span class="font-medium text-ink">{asString(mount.mountpoint)}</span>
										<span class="ml-1.5 text-ink-3">{asString(mount.fstype)}</span>
									</div>
									<div class="flex items-center gap-3 text-ink-2">
										<span>
											{formatBytes(asOptionalNumber(mount.used_bytes))} / {formatBytes(
												asOptionalNumber(mount.total_bytes)
											)}
										</span>
										<span class="tabular font-medium"
											>{formatPercent(asNumber(mount.percent), 1)}</span
										>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex items-center gap-2.5">
		<RefreshCw size={18} class="text-ink-3" aria-hidden="true" />
		<h2 class="text-[17px] font-semibold text-ink">Actualizaciones</h2>
	</div>
	<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[160px_1fr]">
		<dt class="text-ink-3">Reinicio requerido</dt>
		<dd class="font-medium text-ink">{updates.reboot_required === true ? 'Sí' : 'No'}</dd>
		<dt class="text-ink-3">Última actualización</dt>
		<dd class="font-medium text-ink">
			{updates.last_apt_update ? formatDateTime(asString(updates.last_apt_update)) : '—'}
		</dd>
		<dt class="text-ink-3">Paquetes pendientes</dt>
		<dd class="font-medium text-ink">
			{updates.available === null || updates.available === undefined
				? 'No disponible'
				: asNumber(updates.available)}
		</dd>
	</dl>
	{#if updates.reason}
		<p class="mt-2 text-[12px] text-ink-3">{asString(updates.reason)}</p>
	{/if}
</div>
