<script lang="ts">
	import { KeyRound } from '@lucide/svelte';
	import { enhance } from '$app/forms';

	import type { ActionData } from './$types';

	let { form }: { form: ActionData } = $props();
	let submitting = $state(false);

	const inputClass =
		'min-h-11 w-full rounded-[12px] border border-line bg-bg px-3 text-[15px] text-ink outline-none transition-colors focus:border-accent';
</script>

<svelte:head>
	<title>Iniciar sesión · HomeLabDash</title>
</svelte:head>

<div class="flex min-h-dvh items-center justify-center px-4 py-10">
	<div class="w-full max-w-[400px]">
		<div class="flex flex-col items-center text-center">
			<img src="/brand/logo-mark.png" alt="HAPMED" class="h-20 w-20" />
			<p class="mt-3 text-[19px] font-bold tracking-[0.2em] text-ink">HOMELAB</p>
			<p class="mt-1 text-[13px] text-ink-2">Dashboard de monitorización</p>
		</div>

		<div
			class="mt-7 rounded-brand-lg border border-line bg-surface p-6 shadow-[0_24px_70px_-45px_rgba(0,0,0,0.45)]"
		>
			<h1 class="text-[21px] font-semibold tracking-tight text-ink">Iniciar sesión</h1>
			<p class="mt-1 text-[13px] text-ink-2">Acceso privado al servidor HomeLab.</p>

			<form
				method="POST"
				class="mt-5 flex flex-col gap-3"
				use:enhance={() => {
					submitting = true;
					return async ({ update }) => {
						await update();
						submitting = false;
					};
				}}
			>
				<label class="flex flex-col gap-1.5 text-[13px] font-medium text-ink-2">
					<span>Usuario</span>
					<input
						type="text"
						name="username"
						value={form?.username ?? ''}
						required
						autocomplete="username"
						autocapitalize="none"
						spellcheck="false"
						class={inputClass}
					/>
				</label>

				<label class="flex flex-col gap-1.5 text-[13px] font-medium text-ink-2">
					<span>Contraseña</span>
					<input
						type="password"
						name="password"
						required
						autocomplete="current-password"
						class={inputClass}
					/>
				</label>

				{#if form?.error}
					<p role="alert" class="rounded-[10px] bg-danger/10 px-3 py-2 text-[13px] text-danger">
						{form.error}
					</p>
				{/if}

				<button
					type="submit"
					class="mt-1 inline-flex min-h-11 items-center justify-center gap-2 rounded-[12px] bg-accent px-4 text-[14px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
					disabled={submitting}
				>
					<KeyRound size={17} aria-hidden="true" />
					{submitting ? 'Entrando…' : 'Entrar'}
				</button>
			</form>
		</div>

		<p class="mt-4 text-center text-[12px] text-ink-3">
			HomeLabDash · uso privado · sesión protegida por JWT
		</p>
	</div>
</div>
