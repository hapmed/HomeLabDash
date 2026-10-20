<script lang="ts">
	import {
		Cloud,
		CloudDrizzle,
		CloudFog,
		CloudLightning,
		CloudRain,
		CloudSun,
		Snowflake,
		Sun
	} from '@lucide/svelte';

	const icons: Record<string, typeof Cloud> = {
		sun: Sun,
		'cloud-sun': CloudSun,
		cloud: Cloud,
		'cloud-fog': CloudFog,
		'cloud-drizzle': CloudDrizzle,
		'cloud-rain': CloudRain,
		'cloud-lightning': CloudLightning,
		snowflake: Snowflake
	};

	let {
		name,
		size = 24,
		strokeWidth = 1.8
	}: { name: string; size?: number; strokeWidth?: number } = $props();

	const Icon = $derived(icons[name] ?? Cloud);
</script>

<Icon {size} {strokeWidth} aria-hidden="true" />
