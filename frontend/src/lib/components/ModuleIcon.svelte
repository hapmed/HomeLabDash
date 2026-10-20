<script lang="ts">
	import {
		BellRing,
		CircleHelp,
		Cloud,
		Container,
		Cpu,
		DatabaseBackup,
		Gauge,
		Globe,
		HardDrive,
		MemoryStick,
		Network,
		Router,
		Server,
		Thermometer
	} from '@lucide/svelte';

	const icons: Record<string, typeof CircleHelp> = {
		gauge: Gauge,
		cpu: Cpu,
		'memory-stick': MemoryStick,
		'hard-drive': HardDrive,
		globe: Globe,
		container: Container,
		network: Network,
		router: Router,
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
