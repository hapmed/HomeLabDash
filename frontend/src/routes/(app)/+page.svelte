<script lang="ts">
	import { CircleCheck, RotateCw } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { api } from '#lib/api';
	import { formatTime } from '#lib/format';
	import type { ModuleCard as ModuleCardType, ModuleStatus } from '#lib/modules';
	import ModuleCard from '#lib/components/ModuleCard.svelte';
	import OfflineBanner from '#lib/components/OfflineBanner.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let modules = $state<ModuleCardType[]>(data.modules);
	let unavailable = $state(data.unavailable);
	let updatedAt = $state<Date | null>(new Date(data.updatedAt));
	let refreshing = $state(false);

	const counts = $derived.by(() => {
		const result: Record<ModuleStatus, number> = { ok: 0, warn: 0, critical: 0, unknown: 0 };
		for (const module of modules) result[module.status] += 1;
		return result;
	});

	async function refresh() {
		if (typeof document !== 'undefined' && document.hidden) return;
		refreshing = true;
		try {
			const next = await api.modules();
			modules = next;
			unavailable = false;
			updatedAt = new Date();
		} catch {
			unavailable = true;
		} finally {
			refreshing = false;
		}
	}

	onMount(() => {
		const timer = setInterval(refresh, 15000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<title>Panel · HomeLabDash</title>
</svelte:head>

<section class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-4">
		<div>
			<p class="text-[12px] font-semibold tracking-[0.16em] text-ink-3 uppercase">HomeLab</p>
			<h1 class="mt-1 text-[34px] leading-tight font-semibold tracking-tight text-ink">
				Estado del servidor
			</h1>
			<p class="mt-1.5 text-[14px] text-ink-2">
				{modules.length} módulos · actualizado a las {formatTime(updatedAt)}
			</p>
		</div>

		<button
			type="button"
			class="inline-flex min-h-10 items-center gap-2 rounded-[12px] border border-line bg-surface px-3.5 text-[13px] font-medium text-ink-2 transition-colors hover:text-ink disabled:opacity-60"
			onclick={refresh}
			disabled={refreshing}
		>
			<RotateCw size={15} class={refreshing ? 'animate-spin' : ''} aria-hidden="true" />
			{refreshing ? 'Actualizando…' : 'Actualizar'}
		</button>
	</div>

	{#if unavailable}
		<OfflineBanner
			message="El agente de métricas no responde. Se muestra el último estado conocido; los valores pueden estar desactualizados."
		/>
	{/if}

	<div class="flex flex-wrap items-center gap-2 text-[12px] text-ink-3">
		{#if counts.ok > 0}
			<span
				class="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-2.5 py-1 text-success"
			>
				<CircleCheck size={13} aria-hidden="true" />
				{counts.ok} correctos
			</span>
		{/if}
		{#if counts.warn > 0}
			<span class="rounded-full bg-warning/10 px-2.5 py-1 text-warning"
				>{counts.warn} en atención</span
			>
		{/if}
		{#if counts.critical > 0}
			<span class="rounded-full bg-danger/10 px-2.5 py-1 text-danger"
				>{counts.critical} críticos</span
			>
		{/if}
		{#if counts.unknown > 0}
			<span class="rounded-full bg-surface-2 px-2.5 py-1 text-ink-3"
				>{counts.unknown} sin datos</span
			>
		{/if}
	</div>

	{#if modules.length === 0}
		<div class="rounded-brand-lg border border-line bg-surface p-8 text-center">
			<p class="text-[15px] font-medium text-ink">Todavía no hay módulos disponibles</p>
			<p class="mt-1 text-[13px] text-ink-2">
				Comprueba que el backend y el agente estén levantados.
			</p>
			<button
				type="button"
				class="mt-4 rounded-[12px] bg-accent px-4 py-2.5 text-[13px] font-medium text-white"
				onclick={refresh}
			>
				Reintentar
			</button>
		</div>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
			{#each modules as card (card.id)}
				<ModuleCard {card} />
			{/each}
		</div>
	{/if}
</section>
