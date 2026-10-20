<script lang="ts">
	import { CircleX } from '@lucide/svelte';

	import { page } from '$app/state';
</script>

<svelte:head>
	<title>Error · HomeLabDash</title>
</svelte:head>

<div class="flex min-h-dvh items-center justify-center px-4">
	<div class="w-full max-w-[440px] rounded-brand-lg border border-line bg-surface p-8 text-center">
		<CircleX size={34} class="mx-auto text-danger" aria-hidden="true" />
		<h1 class="mt-4 text-[22px] font-semibold text-ink">Algo no ha ido bien</h1>
		<p class="mt-2 text-[14px] text-ink-2">
			{page.error?.message ?? 'Se ha producido un error inesperado.'}
		</p>
		<a
			href="/"
			class="mt-6 inline-flex min-h-11 items-center justify-center rounded-[12px] bg-accent px-4 text-[14px] font-semibold text-white no-underline"
		>
			Volver al panel
		</a>
	</div>
</div>
