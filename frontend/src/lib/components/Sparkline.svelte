<script lang="ts">
	interface Props {
		values: number[];
		color?: string;
		height?: number;
	}

	let { values, color = 'var(--color-accent)', height = 44 }: Props = $props();
	const width = 240;

	const points = $derived.by(() => {
		const clean = values.filter((value) => Number.isFinite(value));
		if (clean.length === 0) return [];
		const min = Math.min(...clean);
		const max = Math.max(...clean);
		const span = max - min || 1;
		const step = clean.length > 1 ? width / (clean.length - 1) : 0;
		const pad = 3;
		const yFor = (value: number) =>
			max === min ? height / 2 : pad + (1 - (value - min) / span) * (height - pad * 2);
		if (clean.length === 1) {
			const y = yFor(clean[0]);
			return [
				{ x: 0, y },
				{ x: width, y }
			];
		}
		return clean.map((value, index) => ({
			x: index * step,
			y: yFor(value)
		}));
	});

	const line = $derived(
		points.length === 0
			? ''
			: points
					.map(
						(point, index) =>
							`${index === 0 ? 'M' : 'L'}${point.x.toFixed(1)},${point.y.toFixed(1)}`
					)
					.join(' ')
	);
	const area = $derived(
		points.length === 0
			? ''
			: `${line} L${points[points.length - 1].x.toFixed(1)},${height} L${points[0].x.toFixed(1)},${height} Z`
	);
</script>

<svg
	viewBox={`0 0 ${width} ${height}`}
	class="h-11 w-full overflow-visible"
	preserveAspectRatio="none"
	role="img"
	aria-label="Serie temporal"
>
	{#if points.length > 0}
		<path d={area} fill={color} opacity="0.10" />
		<path
			d={line}
			fill="none"
			stroke={color}
			stroke-width="1.8"
			stroke-linecap="round"
			stroke-linejoin="round"
			vector-effect="non-scaling-stroke"
		/>
		<circle
			cx={points[points.length - 1].x}
			cy={points[points.length - 1].y}
			r="2.4"
			fill={color}
		/>
	{:else}
		<line
			x1="0"
			y1={height / 2}
			x2={width}
			y2={height / 2}
			stroke="var(--color-line)"
			stroke-width="1"
			stroke-dasharray="4 4"
		/>
	{/if}
</svg>
