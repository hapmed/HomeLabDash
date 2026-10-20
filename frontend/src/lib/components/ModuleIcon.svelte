<script lang="ts">
	import {
		BellRing,
		CircleHelp,
		Cloud,
		CloudSun,
		Container,
		Cpu,
		Database,
		DatabaseBackup,
		Gauge,
		Globe,
		HardDrive,
		Laptop,
		MemoryStick,
		Network,
		Router,
		Server,
		Terminal,
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
		database: Database,
		'cloud-sun': CloudSun,
		terminal: Terminal,
		thermometer: Thermometer,
		laptop: Laptop,
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
