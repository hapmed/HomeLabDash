<script lang="ts">
	import { CircleCheck, CircleHelp, CircleX, TriangleAlert } from '@lucide/svelte';

	import { STATUS_META, type ModuleStatus } from '#lib/modules';

	let { status, compact = false }: { status: ModuleStatus; compact?: boolean } = $props();

	const meta = $derived(STATUS_META[status]);
	const Icon = $derived(
		status === 'ok'
			? CircleCheck
			: status === 'warn'
				? TriangleAlert
				: status === 'critical'
					? CircleX
					: CircleHelp
	);
</script>

<span
	class="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2/70 px-2.5 py-1 text-[12px] font-medium {meta.tone}"
	title={meta.label}
>
	<Icon size={compact ? 13 : 14} strokeWidth={2} aria-hidden="true" />
	<span class={compact ? 'sr-only sm:not-sr-only' : ''}>{meta.label}</span>
</span>
