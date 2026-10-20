<script lang="ts">
	import {
		BellRing,
		CircleHelp,
		Cloud,
		Container,
		Cpu,
		DatabaseBackup,
		Gauge,
		HardDrive,
		MemoryStick,
		Network,
		Server,
		Thermometer
	} from '@lucide/svelte';

	const icons: Record<string, typeof CircleHelp> = {
		gauge: Gauge,
		cpu: Cpu,
		'memory-stick': MemoryStick,
		'hard-drive': HardDrive,
		container: Container,
		network: Network,
		thermometer: Thermometer,
		server: Server,
		cloud: Cloud,
		'database-backup': DatabaseBackup,
		'bell-ring': BellRing
	};

	let {
		name,
		size = 22,
		strokeWidth = 1.8
	}: { name: string; size?: number; strokeWidth?: number } = $props();

	const Icon = $derived(icons[name] ?? CircleHelp);
</script>

<Icon {size} {strokeWidth} aria-hidden="true" />
