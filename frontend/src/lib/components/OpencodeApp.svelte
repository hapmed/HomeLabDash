<script lang="ts">
	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatDateTime, formatNumber } from '#lib/format';
	import StatTile from './StatTile.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

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
</script>

{#if appError}
	<div
		role="status"
		class="rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[13px] text-ink"
	>
		No se pudo consultar la API interna de OpenCode: {appError}. Se muestra solo la información del
		contenedor.
	</div>
{/if}

{#if Object.keys(app).length > 0}
	<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<StatTile
			label="Sesiones"
			value={formatCompact(asNumber(stats.sessions))}
			hint={`${formatCompact(asNumber(stats.subagents))} subagentes`}
		/>
		<StatTile
			label="Pasos"
			value={formatCompact(asNumber(stats.steps))}
			hint={`${formatCompact(asNumber(stats.prompts))} prompts`}
		/>
		<StatTile
			label="Costo"
			value={`$${formatNumber(asOptionalNumber(stats.cost), 2)}`}
			hint={`${asNumber(stats.active_days)} días activos · racha ${asNumber(stats.streak)}`}
		/>
		<StatTile
			label="Tokens"
			value={formatCompact(
				asNumber(tokens.input) + asNumber(tokens.output) + asNumber(tokens.reasoning)
			)}
			hint={`${formatCompact(asNumber(tokens.cache_read))} en caché`}
		/>
	</div>

	<div class="grid gap-4 lg:grid-cols-2">
		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Aplicación</h2>
			<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[150px_1fr]">
				<dt class="text-ink-3">Versión</dt>
				<dd class="font-medium text-ink">{asString(info.version, '—')}</dd>
				<dt class="text-ink-3">PID</dt>
				<dd class="font-medium text-ink">{asNumber(info.pid)}</dd>
				<dt class="text-ink-3">Modelo por defecto</dt>
				<dd class="font-medium text-ink">
					{asString(defaultModel.name, asString(defaultModel.id, '—'))}
					{#if asString(defaultModel.provider, '')}· {asString(defaultModel.provider)}{/if}
				</dd>
				<dt class="text-ink-3">Agentes</dt>
				<dd class="font-medium text-ink">
					{agents.length}
					{#if agents.length > 0}
						· {agents
							.slice(0, 4)
							.map((agent) => asString(agent.id, ''))
							.filter(Boolean)
							.join(', ')}
					{/if}
				</dd>
				<dt class="text-ink-3">Directorio</dt>
				<dd class="break-all font-medium text-ink">{asString(location.directory, '—')}</dd>
				<dt class="text-ink-3">Zona horaria</dt>
				<dd class="font-medium text-ink">{asString(app.timezone, '—')}</dd>
				<dt class="text-ink-3">Sesiones activas</dt>
				<dd class="font-medium text-ink">
					{active.length > 0
						? active
								.map((item) => asString(item.title, asString(item.id)))
								.slice(0, 3)
								.join(', ')
						: 'Ninguna'}
				</dd>
				<dt class="text-ink-3">URLs</dt>
				<dd class="break-all font-mono text-[11px] text-ink-2">
					{asArray(info.urls)
						.map((item) => asString(item, ''))
						.filter(Boolean)
						.join(', ') || '—'}
				</dd>
			</dl>
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Uso y herramientas</h2>
			<dl class="mt-4 grid gap-x-4 gap-y-3 text-[13px] sm:grid-cols-[160px_1fr]">
				<dt class="text-ink-3">Llamadas a herramientas</dt>
				<dd class="font-medium text-ink">
					{formatCompact(asNumber(tools.calls))} · {formatCompact(asNumber(tools.succeeded))} ok · {formatCompact(
						asNumber(tools.failed)
					)} fallidas
				</dd>
				<dt class="text-ink-3">Tokens de entrada</dt>
				<dd class="font-medium text-ink">{formatCompact(asNumber(tokens.input))}</dd>
				<dt class="text-ink-3">Tokens de salida</dt>
				<dd class="font-medium text-ink">{formatCompact(asNumber(tokens.output))}</dd>
				<dt class="text-ink-3">Razonamiento</dt>
				<dd class="font-medium text-ink">{formatCompact(asNumber(tokens.reasoning))}</dd>
				<dt class="text-ink-3">Caché lectura / escritura</dt>
				<dd class="font-medium text-ink">
					{formatCompact(asNumber(tokens.cache_read))} /
					{formatCompact(asNumber(tokens.cache_write))}
				</dd>
				<dt class="text-ink-3">Costo estimado</dt>
				<dd class="font-medium text-ink">${formatNumber(asOptionalNumber(stats.cost), 2)}</dd>
			</dl>
		</div>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-[17px] font-semibold text-ink">Proyectos</h2>
			<span class="text-[12px] text-ink-3">actividad reciente</span>
		</div>
		{#if projects.length === 0}
			<p class="mt-4 text-[13px] text-ink-3">Sin proyectos.</p>
		{:else}
			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[760px] border-collapse text-[12px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Proyecto</th>
							<th class="pb-2 pr-4 font-medium">VCS</th>
							<th class="pb-2 pr-4 font-medium">Sesiones</th>
							<th class="pb-2 pr-4 font-medium">Costo</th>
							<th class="pb-2 pr-4 font-medium">Tokens</th>
							<th class="pb-2 font-medium">Última actividad</th>
						</tr>
					</thead>
					<tbody>
						{#each projects as project (project.id)}
							<tr class="border-b border-line/60 last:border-0">
								<td class="break-all py-2.5 pr-4 font-medium text-ink">
									{asString(project.canonical)}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(project.vcs, '—')}</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatCompact(asNumber(project.sessions))}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									${formatNumber(asOptionalNumber(project.cost), 2)}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatCompact(
										asNumber(asObject(project.tokens).input) +
											asNumber(asObject(project.tokens).output)
									)}
								</td>
								<td class="py-2.5 text-ink-2">{formatEpoch(project.last_active)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-[17px] font-semibold text-ink">Sesiones recientes</h2>
			<span class="text-[12px] text-ink-3">últimas {sessions.length}</span>
		</div>
		{#if sessions.length === 0}
			<p class="mt-4 text-[13px] text-ink-3">Sin sesiones.</p>
		{:else}
			<div class="mt-4 overflow-x-auto">
				<table class="w-full min-w-[980px] border-collapse text-[12px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Título</th>
							<th class="pb-2 pr-4 font-medium">Proyecto</th>
							<th class="pb-2 pr-4 font-medium">Agente</th>
							<th class="pb-2 pr-4 font-medium">Modelo</th>
							<th class="pb-2 pr-4 font-medium">Costo</th>
							<th class="pb-2 pr-4 font-medium">Tokens</th>
							<th class="pb-2 pr-4 font-medium">Resultado</th>
							<th class="pb-2 font-medium">Actualizada</th>
						</tr>
					</thead>
					<tbody>
						{#each sessions.slice(0, 20) as session (session.id)}
							<tr class="border-b border-line/60 last:border-0">
								<td
									class="max-w-[260px] truncate py-2.5 pr-4 font-medium text-ink"
									title={asString(session.title)}
								>
									{asString(session.title)}
								</td>
								<td class="break-all py-2.5 pr-4 text-ink-2">
									{asString(session.project_path, asString(session.directory, '—'))}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(session.agent, '—')}</td>
								<td class="py-2.5 pr-4 text-ink-2">{modelName(session.model)}</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									${formatNumber(asOptionalNumber(session.cost), 2)}
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatCompact(
										asNumber(asObject(session.tokens).input) +
											asNumber(asObject(session.tokens).output)
									)}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">{asString(session.outcome, '—')}</td>
								<td class="py-2.5 text-ink-2">{formatEpoch(session.updated_at)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>

	<div class="grid gap-4 lg:grid-cols-2">
		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Modelos</h2>
			{#if models.length === 0}
				<p class="mt-4 text-[13px] text-ink-3">Sin datos de modelos.</p>
			{:else}
				<div class="mt-4 flex flex-col gap-3 text-[12px]">
					{#each models as model (asString(model.id) + asString(model.provider))}
						<div
							class="flex items-center justify-between gap-3 border-b border-line/60 pb-2 last:border-0"
						>
							<div>
								<p class="font-medium text-ink">{asString(model.id)}</p>
								<p class="text-ink-3">
									{asString(model.provider, '—')}
									{#if asString(model.variant, '')}· {asString(model.variant)}{/if}
								</p>
							</div>
							<div class="text-right">
								<p class="tabular font-medium text-ink">
									${formatNumber(asOptionalNumber(model.cost), 2)}
								</p>
								<p class="text-ink-3">{formatCompact(asNumber(model.steps))} pasos</p>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<div class="rounded-brand-lg border border-line bg-surface p-5">
			<h2 class="text-[17px] font-semibold text-ink">Actividad</h2>
			{#if activity.length === 0}
				<p class="mt-4 text-[13px] text-ink-3">Sin actividad.</p>
			{:else}
				<div class="mt-4 flex flex-col gap-2">
					{#each activity as day (day.date)}
						{@const steps = asNumber(day.steps)}
						<div class="flex items-center gap-3 text-[12px]">
							<span class="w-20 shrink-0 text-ink-3">{asString(day.date)}</span>
							<div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
								<div
									class="h-full rounded-full bg-accent"
									style:width={`${Math.max(2, (steps / maxActivity) * 100)}%`}
								></div>
							</div>
							<span class="tabular w-10 text-right text-ink-2">{formatCompact(steps)}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
