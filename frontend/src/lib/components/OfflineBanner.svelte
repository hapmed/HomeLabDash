<script lang="ts">
	import { WifiOff } from '@lucide/svelte';

	let { message }: { message: string } = $props();
</script>

<div
	role="status"
	class="flex items-start gap-3 rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[14px] text-ink"
>
	<WifiOff size={18} class="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
	<p>{message}</p>
</div>
