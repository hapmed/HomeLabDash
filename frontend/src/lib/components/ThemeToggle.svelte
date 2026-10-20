<script lang="ts">
	import { Moon, Sun } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { currentTheme, toggleTheme, type Theme } from '#lib/theme';

	let theme = $state<Theme>('light');

	onMount(() => {
		theme = currentTheme();
	});

	function onToggle() {
		theme = toggleTheme();
	}
</script>

<button
	type="button"
	class="inline-flex h-10 w-10 items-center justify-center rounded-[12px] border border-line bg-surface text-ink-2 transition-colors hover:text-ink"
	onclick={onToggle}
	aria-label={theme === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
	title={theme === 'dark' ? 'Tema claro' : 'Tema oscuro'}
>
	{#if theme === 'dark'}
		<Sun size={18} aria-hidden="true" />
	{:else}
		<Moon size={18} aria-hidden="true" />
	{/if}
</button>
