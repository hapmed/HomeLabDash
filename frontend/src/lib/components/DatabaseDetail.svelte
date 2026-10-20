<script lang="ts">
	import { asArray, asNumber, asObject, asOptionalNumber, asString, usageTone } from '#lib/detail';
	import {
		formatBytes,
		formatDateTime,
		formatNumber,
		formatPercent,
		formatUptime
	} from '#lib/format';
	import DbSizeChart from './DbSizeChart.svelte';
	import Meter from './Meter.svelte';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const database = $derived(asObject(detail.database));
	const connections = $derived(asObject(detail.connections));
	const activity = $derived(asObject(detail.activity));
	const tables = $derived(asArray(detail.tables).map(asObject));
	const indexes = $derived(asArray(detail.indexes).map(asObject));
	const settings = $derived(asObject(detail.settings));
	const alerts = $derived(asArray(detail.alerts).map((item) => asString(item, '')));
	const name = $derived(asString(database.name, 'homelabdash'));
	const version = $derived(asString(database.version, 'PostgreSQL'));
	const serverVersion = $derived(asString(database.server_version, ''));
	const sizePretty = $derived(asString(database.size_pretty, '—'));
	const sizeBytes = $derived(asOptionalNumber(database.size_bytes));
	const tableCount = $derived(asNumber(database.tables, 0));
	const indexCount = $derived(asNumber(database.indexes, 0));
	const startedAt = $derived(asString(database.started_at, ''));
	const uptime = $derived(asNumber(database.uptime_seconds, 0));
	const currentConnections = $derived(asNumber(connections.current, 0));
	const maxConnections = $derived(asNumber(connections.max, 0));
	const connectionPercent = $derived(asNumber(connections.percent, 0));
	const activeConnections = $derived(asNumber(connections.active, 0));
	const idleConnections = $derived(asNumber(connections.idle, 0));
	const idleTx = $derived(asNumber(connections.idle_in_transaction, 0));
	const waitingLocks = $derived(asNumber(connections.waiting_locks, 0));
	const longestQuery = $derived(asNumber(connections.longest_query_seconds, 0));
	const longestTransaction = $derived(asNumber(connections.longest_transaction_seconds, 0));
	const cacheHit = $derived(asNumber(activity.cache_hit_ratio, 0));
	const commits = $derived(asNumber(activity.xact_commit, 0));
	const rollbacks = $derived(asNumber(activity.xact_rollback, 0));
	const blocksRead = $derived(asNumber(activity.blks_read, 0));
	const blocksHit = $derived(asNumber(activity.blks_hit, 0));
	const tempBytes = $derived(asNumber(activity.temp_bytes, 0));
	const tempFiles = $derived(asNumber(activity.temp_files, 0));
	const deadlocks = $derived(asNumber(activity.deadlocks, 0));
	const conflicts = $derived(asNumber(activity.conflicts, 0));
	const inserted = $derived(asNumber(activity.tup_inserted, 0));
	const updated = $derived(asNumber(activity.tup_updated, 0));
	const deleted = $derived(asNumber(activity.tup_deleted, 0));
	const deadTuples = $derived(asNumber(activity.dead_tuples, 0));
	const liveTuples = $derived(asNumber(activity.live_tuples, 0));
	const deadRatio = $derived(asNumber(activity.dead_ratio, 0));
	const statsReset = $derived(asString(activity.stats_reset, ''));

	function cacheStatus(value: number): 'ok' | 'warn' | 'critical' {
		if (value >= 90) return 'ok';
		if (value >= 80) return 'warn';
		return 'critical';
	}

	function setting(name: string): string {
		const item = asObject(settings[name]);
		const value = asString(item.setting, '—');
		const unit = asString(item.unit, '');
		return unit ? `${value} ${unit}` : value;
	}
</script>

{#if alerts.length > 0}
	<div
		role="status"
		class="rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[13px] text-ink"
	>
		<p class="font-medium">Avisos de la base de datos</p>
		<ul class="mt-1 list-inside list-disc text-ink-2">
			{#each alerts as alert}
				<li>{alert}</li>
			{/each}
		</ul>
	</div>
{/if}

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile
		label="Tamaño"
		value={sizePretty}
		hint={`${tableCount} tablas · ${indexCount} índices`}
	/>
	<StatTile
		label="Conexiones"
		value={`${currentConnections}/${maxConnections}`}
		hint={`${formatPercent(connectionPercent, 1)} del máximo`}
	/>
	<StatTile label="Caché" value={formatPercent(cacheHit, 1)} hint="bloques desde memoria" />
	<StatTile
		label="Tuplas muertas"
		value={formatPercent(deadRatio, 1)}
		hint={`${formatNumber(deadTuples, 0)} de ${formatNumber(liveTuples + deadTuples, 0)}`}
	/>
</div>

<div class="grid gap-4 lg:grid-cols-2">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Base de datos</h2>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[140px_1fr]">
			<dt class="text-ink-3">Nombre</dt>
			<dd class="font-medium text-ink">{name}</dd>
			<dt class="text-ink-3">Versión</dt>
			<dd class="font-medium text-ink">
				{version}
				{#if serverVersion && serverVersion !== version}· {serverVersion}{/if}
			</dd>
			<dt class="text-ink-3">Tamaño</dt>
			<dd class="font-medium text-ink">{sizePretty} ({formatBytes(sizeBytes)})</dd>
			<dt class="text-ink-3">Tablas / índices</dt>
			<dd class="font-medium text-ink">{tableCount} / {indexCount}</dd>
			<dt class="text-ink-3">Arranque</dt>
			<dd class="font-medium text-ink">
				{formatDateTime(startedAt)} · {formatUptime(uptime)}
			</dd>
		</dl>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Conexiones y memoria</h2>
		<div class="mt-5 flex flex-col gap-5">
			<Meter
				label="Uso de conexiones"
				value={connectionPercent}
				status={usageTone(connectionPercent)}
				detail={`${currentConnections} de ${maxConnections} conexiones`}
			/>
			<Meter
				label="Caché de bloques"
				value={cacheHit}
				status={cacheStatus(cacheHit)}
				detail={`${formatNumber(blocksHit, 0)} aciertos · ${formatNumber(blocksRead, 0)} lecturas`}
			/>
		</div>
		<dl
			class="mt-5 grid gap-x-4 gap-y-3 border-t border-line pt-4 text-[13px] sm:grid-cols-[150px_1fr]"
		>
			<dt class="text-ink-3">Activas / idle</dt>
			<dd class="font-medium text-ink">
				{activeConnections} / {idleConnections} · {idleTx} en transacción
			</dd>
			<dt class="text-ink-3">Bloqueos en espera</dt>
			<dd class="font-medium text-ink">{waitingLocks}</dd>
			<dt class="text-ink-3">Consulta más larga</dt>
			<dd class="font-medium text-ink">{formatNumber(longestQuery, 1)} s</dd>
			<dt class="text-ink-3">Transacción más larga</dt>
			<dd class="font-medium text-ink">{formatNumber(longestTransaction, 1)} s</dd>
		</dl>
	</div>
</div>

<div class="grid gap-4 lg:grid-cols-2">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Actividad acumulada</h2>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[160px_1fr]">
			<dt class="text-ink-3">Commits / rollbacks</dt>
			<dd class="font-medium text-ink">
				{formatNumber(commits, 0)} / {formatNumber(rollbacks, 0)}
			</dd>
			<dt class="text-ink-3">Insertadas / actualizadas</dt>
			<dd class="font-medium text-ink">
				{formatNumber(inserted, 0)} / {formatNumber(updated, 0)}
			</dd>
			<dt class="text-ink-3">Borradas / muertas</dt>
			<dd class="font-medium text-ink">
				{formatNumber(deleted, 0)} / {formatNumber(deadTuples, 0)}
			</dd>
			<dt class="text-ink-3">Temp</dt>
			<dd class="font-medium text-ink">
				{formatBytes(tempBytes)} en {formatNumber(tempFiles, 0)} archivos
			</dd>
			<dt class="text-ink-3">Deadlocks / conflictos</dt>
			<dd class="font-medium text-ink">
				{formatNumber(deadlocks, 0)} / {formatNumber(conflicts, 0)}
			</dd>
			<dt class="text-ink-3">Reset de estadísticas</dt>
			<dd class="font-medium text-ink">{formatDateTime(statsReset)}</dd>
		</dl>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<h2 class="text-[17px] font-semibold text-ink">Configuración</h2>
		<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[170px_1fr]">
			<dt class="text-ink-3">max_connections</dt>
			<dd class="font-medium text-ink">{setting('max_connections')}</dd>
			<dt class="text-ink-3">shared_buffers</dt>
			<dd class="font-medium text-ink">{setting('shared_buffers')}</dd>
			<dt class="text-ink-3">work_mem</dt>
			<dd class="font-medium text-ink">{setting('work_mem')}</dd>
			<dt class="text-ink-3">maintenance_work_mem</dt>
			<dd class="font-medium text-ink">{setting('maintenance_work_mem')}</dd>
			<dt class="text-ink-3">effective_cache_size</dt>
			<dd class="font-medium text-ink">{setting('effective_cache_size')}</dd>
			<dt class="text-ink-3">autovacuum</dt>
			<dd class="font-medium text-ink">{setting('autovacuum')}</dd>
		</dl>
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Histórico de tamaño</h2>
		<span class="text-[12px] text-ink-3">muestra cada 5 min · 24 h</span>
	</div>
	<div class="mt-4">
		<DbSizeChart history={detail.history} />
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Tablas</h2>
		<span class="text-[12px] text-ink-3">top {tables.length} por tamaño</span>
	</div>
	{#if tables.length === 0}
		<p class="mt-4 text-[13px] text-ink-3">Sin tablas de usuario.</p>
	{:else}
		<div class="mt-4 overflow-x-auto">
			<table class="w-full min-w-[1050px] border-collapse text-[12px]">
				<thead>
					<tr class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase">
						<th class="pb-2 pr-4 font-medium">Tabla</th>
						<th class="pb-2 pr-4 font-medium">Filas</th>
						<th class="pb-2 pr-4 font-medium">Muertas</th>
						<th class="pb-2 pr-4 font-medium">Tamaño</th>
						<th class="pb-2 pr-4 font-medium">Heap / índice</th>
						<th class="pb-2 pr-4 font-medium">Seq scans</th>
						<th class="pb-2 pr-4 font-medium">Index scans</th>
						<th class="pb-2 pr-4 font-medium">Último vacuum</th>
						<th class="pb-2 font-medium">Último analyze</th>
					</tr>
				</thead>
				<tbody>
					{#each tables as table (asString(table.schema) + '.' + asString(table.name))}
						<tr class="border-b border-line/60 last:border-0">
							<td class="py-2.5 pr-4 font-medium text-ink">
								{asString(table.schema)}.{asString(table.name)}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatNumber(asNumber(table.rows), 0)}
							</td>
							<td
								class="tabular py-2.5 pr-4 {asNumber(table.dead_rows) > 0
									? 'text-warning'
									: 'text-ink-2'}"
							>
								{formatNumber(asNumber(table.dead_rows), 0)}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatBytes(asOptionalNumber(table.total_bytes))}
							</td>
							<td class="tabular py-2.5 pr-4 text-[11px] text-ink-3">
								{formatBytes(asOptionalNumber(table.heap_bytes))} /
								{formatBytes(asOptionalNumber(table.index_bytes))}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatNumber(asNumber(table.seq_scan), 0)}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatNumber(asNumber(table.idx_scan), 0)}
							</td>
							<td class="py-2.5 pr-4 text-[11px] text-ink-3">
								{formatDateTime(asString(table.last_vacuum, ''))}
								{#if asString(table.last_autovacuum, '')}
									<br /><span>auto {formatDateTime(asString(table.last_autovacuum, ''))}</span>
								{/if}
							</td>
							<td class="py-2.5 text-[11px] text-ink-3">
								{formatDateTime(asString(table.last_analyze, ''))}
								{#if asString(table.last_autoanalyze, '')}
									<br /><span>auto {formatDateTime(asString(table.last_autoanalyze, ''))}</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Índices</h2>
		<span class="text-[12px] text-ink-3">top {indexes.length} por tamaño</span>
	</div>
	{#if indexes.length === 0}
		<p class="mt-4 text-[13px] text-ink-3">Sin índices de usuario.</p>
	{:else}
		<div class="mt-4 overflow-x-auto">
			<table class="w-full min-w-[760px] border-collapse text-[12px]">
				<thead>
					<tr class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase">
						<th class="pb-2 pr-4 font-medium">Tabla</th>
						<th class="pb-2 pr-4 font-medium">Índice</th>
						<th class="pb-2 pr-4 font-medium">Tamaño</th>
						<th class="pb-2 pr-4 font-medium">Scans</th>
						<th class="pb-2 font-medium">Tuplas leídas</th>
					</tr>
				</thead>
				<tbody>
					{#each indexes as index (asString(index.schema) + '.' + asString(index.name))}
						<tr class="border-b border-line/60 last:border-0">
							<td class="py-2.5 pr-4 text-ink-2">
								{asString(index.schema)}.{asString(index.table)}
							</td>
							<td class="py-2.5 pr-4 font-medium text-ink">{asString(index.name)}</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatBytes(asOptionalNumber(index.size_bytes))}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatNumber(asNumber(index.scans), 0)}
							</td>
							<td class="tabular py-2.5 text-ink-2">
								{formatNumber(asNumber(index.tuples_read), 0)}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<p class="text-[12px] leading-5 text-ink-3">
	Estadísticas de solo lectura de la base <strong>{name}</strong> en la instancia PostgreSQL existente.
	No se consultan ni modifican otras bases. El histórico se guarda cada 5 minutos y se conserva 30 días.
</p>
