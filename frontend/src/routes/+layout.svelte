<script lang="ts">
	import { onMount } from 'svelte';

	import '../app.css';

	let { children } = $props();

	onMount(() => {
		if (import.meta.env.PROD && 'serviceWorker' in navigator) {
			navigator.serviceWorker.register('/sw.js').catch(() => {
				/* la app funciona sin service worker */
			});
		}
	});
</script>

{@render children()}
