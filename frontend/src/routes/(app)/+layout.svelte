<script lang="ts">
	import { LogOut } from '@lucide/svelte';

	import ThemeToggle from '#lib/components/ThemeToggle.svelte';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: import('svelte').Snippet } = $props();
</script>

<div class="min-h-dvh">
	<header class="material sticky top-0 z-30 border-b border-line">
		<div class="mx-auto flex h-16 max-w-[1200px] items-center gap-3 px-4 sm:px-6">
			<a href="/" class="flex items-center gap-2.5 no-underline" aria-label="HomeLabDash — Panel">
				<img src="/brand/logo-mark.png" alt="" class="h-8 w-8" />
				<span class="text-[16px] font-bold tracking-[0.14em] text-ink">HOMELAB</span>
			</a>

			<nav class="ml-4 hidden items-center gap-1 sm:flex" aria-label="Principal">
				<a
					href="/"
					class="rounded-[10px] px-3 py-2 text-[13px] font-medium text-ink-2 no-underline transition-colors hover:bg-surface-2 hover:text-ink"
				>
					Panel
				</a>
			</nav>

			<div class="ml-auto flex items-center gap-2">
				{#if data.user}
					<span class="hidden text-[13px] text-ink-3 sm:inline">{data.user.username}</span>
				{/if}
				<ThemeToggle />
				<form method="POST" action="/logout">
					<button
						type="submit"
						class="inline-flex h-10 w-10 items-center justify-center rounded-[12px] border border-line bg-surface text-ink-2 transition-colors hover:text-danger"
						aria-label="Cerrar sesión"
						title="Cerrar sesión"
					>
						<LogOut size={17} aria-hidden="true" />
					</button>
				</form>
			</div>
		</div>
	</header>

	<main class="mx-auto w-full max-w-[1200px] px-4 py-8 sm:px-6 sm:py-10">
		{@render children()}
	</main>

	<footer class="mx-auto max-w-[1200px] px-4 pb-8 sm:px-6">
		<p class="border-t border-line pt-5 text-[12px] text-ink-3">
			HomeLabDash · monitorización del HomeLab · datos en vivo del agente
		</p>
	</footer>
</div>
