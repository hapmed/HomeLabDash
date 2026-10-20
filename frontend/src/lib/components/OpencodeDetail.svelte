<script lang="ts">
	import { onMount } from 'svelte';

	import { api } from '#lib/api';
	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import {
		formatBytes,
		formatDateTime,
		formatNumber,
		formatPercent,
		formatUptime
	} from '#lib/format';
	import OpencodeApp from './OpencodeApp.svelte';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const container = $derived(asObject(detail.container));
	const inspect = $derived(asObject(container.inspect));
	const mounts = $derived(asArray(inspect.mounts).map(asObject));
	const envKeys = $derived(asArray(inspect.env_keys).map((item) => asString(item, '')));
	const ports = $derived(asArray(container.ports).map((item) => asString(item, '')));
	const networks = $derived(asArray(container.networks).map((item) => asString(item, '')));
	const containerState = $derived(asString(container.state, '—'));
	const health = $derived(asString(container.health, ''));

	const app = $derived(asObject(detail.app));
	const appError = $derived(asString(detail.app_error, ''));
	const info = $derived(asObject(app.info));
	const stats = $derived(asObject(app.stats));
	const projects = $derived(asArray(app.projects).map(asObject));
	const sessions = $derived(asArray(app.sessions).map(asObject));
	const active = $derived(asArray(app.active).map(asObject));
	const defaultModel = $derived(asObject(app.default_model));
	const agents = $derived(asArray(app.agents).map(asObject));
	const location = $derived(asObject(app.location));
	const activity = $derived(asArray(stats.activity).map(asObject));
	const models = $derived(asArray(stats.models).map(asObject));
	const tokens = $derived(asObject(stats.tokens));
	const tools = $derived(asObject(stats.tools));
	const maxActivity = $derived(Math.max(1, ...activity.map((item) => asNumber(item.steps, 0))));

	function formatCompact(value: number): string {
		return new Intl.NumberFormat('es-ES', {
			notation: 'compact',
			maximumFractionDigits: 1
		}).format(value);
	}

	function formatEpoch(value: unknown): string {
		const milliseconds = asOptionalNumber(value);
		return milliseconds ? formatDateTime(new Date(milliseconds)) : '—';
	}

	function modelName(value: unknown): string {
		const model = asObject(value);
		const id = asString(model.id, '—');
		const provider = asString(model.provider, '');
		return provider ? `${id} · ${provider}` : id;
	}

	let logLines = $state<string[]>([]);
	let logLoading = $state(false);
	let logError = $state<string | null>(null);

	function listText(value: unknown): string {
		const values = asArray(value);
		return values.length ? values.map((item) => asString(item, '')).join(' ') : '—';
	}

	async function loadLogs() {
		logLoading = true;
		logError = null;
		try {
			const result = await api.dockerLogs(asString(container.name, 'opencode'), 100);
			logLines = result.lines;
		} catch {
			logError = 'No se pudieron cargar los logs.';
		} finally {
			logLoading = false;
		}
	}

	onMount(() => {
		void loadLogs();
	});
</script>

{#if asString(detail.error, '')}
	<div
		role="status"
		class="rounded-brand-lg border border-danger/30 bg-danger/10 px-4 py-3 text-[13px] text-ink"
	>
		{asString(detail.error)}
	</div>
{/if}

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile
		label="Estado"
		value={containerState}
		hint={health ? `salud: ${health}` : asString(container.status, '')}
	/>
	<StatTile
		label="CPU"
		value={formatPercent(asOptionalNumber(container.cpu_percent), 1)}
		hint={`${asNumber(container.pids)} procesos`}
	/>
	<StatTile
		label="RAM"
		value={formatBytes(asOptionalNumber(container.memory_used))}
		hint={`de ${formatBytes(asOptionalNumber(container.memory_limit))} · ${formatPercent(
			asOptionalNumber(container.memory_percent),
			1
		)}`}
	/>
	<StatTile
		label="Uptime"
		value={formatUptime(asNumber(container.uptime_seconds, 0))}
		hint={`${asNumber(container.restart_count)} reinicios`}
	/>
</div>

<div class="grid gap-4 lg:grid-cols-2">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Contenedor</h2>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[150px_1fr]">
			<dt class="text-ink-3">Nombre</dt>
			<dd class="font-medium text-ink">{asString(container.name)}</dd>
			<dt class="text-ink-3">Imagen</dt>
			<dd class="break-all font-medium text-ink">{asString(container.image)}</dd>
			<dt class="text-ink-3">ID</dt>
			<dd class="font-mono text-[12px] text-ink-2">{asString(container.id)}</dd>
			<dt class="text-ink-3">Creado</dt>
			<dd class="font-medium text-ink">{formatDateTime(asString(container.created, ''))}</dd>
			<dt class="text-ink-3">Arrancado</dt>
			<dd class="font-medium text-ink">{formatDateTime(asString(container.started_at, ''))}</dd>
			<dt class="text-ink-3">Compose</dt>
			<dd class="font-medium text-ink">
				{asString(container.compose_project, '—')}/{asString(container.compose_service, '—')}
			</dd>
			<dt class="text-ink-3">Comando</dt>
			<dd class="break-all font-mono text-[12px] text-ink-2">
				{listText(inspect.entrypoint)}
				{listText(inspect.command)}
			</dd>
			<dt class="text-ink-3">Working dir</dt>
			<dd class="font-medium text-ink">{asString(inspect.working_dir)}</dd>
			<dt class="text-ink-3">Usuario</dt>
			<dd class="font-medium text-ink">{asString(inspect.user, 'root')}</dd>
			<dt class="text-ink-3">Restart / red</dt>
			<dd class="font-medium text-ink">
				{asString(inspect.restart_policy, '—')} · {asString(inspect.network_mode, '—')}
			</dd>
		</dl>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Consumo</h2>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[150px_1fr]">
			<dt class="text-ink-3">CPU</dt>
			<dd class="font-medium text-ink">
				{formatPercent(asOptionalNumber(container.cpu_percent), 1)}
			</dd>
			<dt class="text-ink-3">RAM</dt>
			<dd class="font-medium text-ink">
				{formatBytes(asOptionalNumber(container.memory_used))} /
				{formatBytes(asOptionalNumber(container.memory_limit))}
			</dd>
			<dt class="text-ink-3">Red RX / TX</dt>
			<dd class="font-medium text-ink">
				{formatBytes(asOptionalNumber(container.net_rx))} /
				{formatBytes(asOptionalNumber(container.net_tx))}
			</dd>
			<dt class="text-ink-3">Disco R / W</dt>
			<dd class="font-medium text-ink">
				{formatBytes(asOptionalNumber(container.blk_read))} /
				{formatBytes(asOptionalNumber(container.blk_write))}
			</dd>
			<dt class="text-ink-3">PIDs</dt>
			<dd class="font-medium text-ink">{asNumber(container.pids)}</dd>
			<dt class="text-ink-3">Puertos</dt>
			<dd class="font-medium text-ink">
				{ports.length > 0 ? ports.join(', ') : '—'}
			</dd>
			<dt class="text-ink-3">Redes</dt>
			<dd class="font-medium text-ink">
				{networks.length > 0 ? networks.join(', ') : '—'}
			</dd>
		</dl>
	</div>
</div>

<OpencodeApp {detail} />

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<h2 class="text-[17px] font-semibold text-ink">Montajes</h2>
	{#if mounts.length === 0}
		<p class="mt-4 text-[13px] text-ink-3">Sin montajes.</p>
	{:else}
		<div class="mt-4 overflow-x-auto">
			<table class="w-full min-w-[760px] border-collapse text-[12px]">
				<thead>
					<tr class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase">
						<th class="pb-2 pr-4 font-medium">Tipo</th>
						<th class="pb-2 pr-4 font-medium">Origen</th>
						<th class="pb-2 pr-4 font-medium">Destino</th>
						<th class="pb-2 font-medium">Modo</th>
					</tr>
				</thead>
				<tbody>
					{#each mounts as mount (asString(mount.source) + asString(mount.destination))}
						<tr class="border-b border-line/60 last:border-0">
							<td class="py-2.5 pr-4 text-ink-2">{asString(mount.type)}</td>
							<td class="break-all py-2.5 pr-4 font-mono text-[11px] text-ink-2">
								{asString(mount.source)}
							</td>
							<td class="break-all py-2.5 pr-4 font-mono text-[11px] text-ink">
								{asString(mount.destination)}
							</td>
							<td class="py-2.5 text-ink-2">
								{mount.rw === true ? 'lectura/escritura' : 'solo lectura'}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<h2 class="text-[17px] font-semibold text-ink">Variables de entorno</h2>
	<p class="mt-1 text-[12px] text-ink-3">Solo nombres; los valores no se muestran.</p>
	<div class="mt-4 flex flex-wrap gap-2">
		{#each envKeys as key}
			<span
				class="rounded-full border border-line bg-surface-2/60 px-2.5 py-1 font-mono text-[11px] text-ink-2"
			>
				{key}
			</span>
		{/each}
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Logs</h2>
		<button
			type="button"
			class="inline-flex min-h-9 items-center rounded-[10px] border border-line bg-surface px-3 text-[12px] font-medium text-ink-2 transition-colors hover:text-ink disabled:opacity-60"
			onclick={loadLogs}
			disabled={logLoading}
		>
			{logLoading ? 'Cargando…' : 'Actualizar'}
		</button>
	</div>
	{#if logError}
		<p class="mt-3 text-[13px] text-danger">{logError}</p>
	{/if}
	<pre
		class="mt-3 max-h-[460px] overflow-auto rounded-brand border border-line bg-surface-2/50 p-3 text-[11px] leading-5 whitespace-pre-wrap text-ink-2">{#if logLines.length > 0}{logLines.join(
				'\n'
			)}{:else}Sin líneas de log.{/if}</pre>
</div>

<p class="text-[12px] leading-5 text-ink-3">
	Información de solo lectura del contenedor OpenCode: estado, recursos, configuración e montajes
	obtenidos del socket Docker; los logs se leen bajo demanda.
</p>
