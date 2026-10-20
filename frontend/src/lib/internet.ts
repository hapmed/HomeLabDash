import { asArray, asObject, asOptionalNumber, asString } from '#lib/detail';

export interface SpeedSample {
	at: string;
	download_mbps: number | null;
	upload_mbps: number | null;
	latency_ms: number | null;
}

export interface ChartPadding {
	top: number;
	right: number;
	bottom: number;
	left: number;
}

export function parseHistory(value: unknown): SpeedSample[] {
	return asArray(value)
		.map(asObject)
		.map((item) => ({
			at: asString(item.at, ''),
			download_mbps: asOptionalNumber(item.download_mbps),
			upload_mbps: asOptionalNumber(item.upload_mbps),
			latency_ms: asOptionalNumber(item.latency_ms)
		}))
		.filter((sample) => sample.at !== '');
}

export function niceCeil(value: number): number {
	if (!Number.isFinite(value) || value <= 0) return 1;
	const magnitude = 10 ** Math.floor(Math.log10(value));
	const normalized = value / magnitude;
	const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
	return step * magnitude;
}

export function chartMax(samples: SpeedSample[]): number {
	const values = samples.flatMap((sample) => [sample.download_mbps ?? 0, sample.upload_mbps ?? 0]);
	return niceCeil(Math.max(1, ...values));
}

export function chartPoints(
	values: number[],
	width: number,
	height: number,
	max: number,
	padding: ChartPadding
): string {
	const plotWidth = Math.max(1, width - padding.left - padding.right);
	const plotHeight = Math.max(1, height - padding.top - padding.bottom);
	const safeMax = Math.max(1, max);
	return values
		.map((value, index) => {
			const x =
				padding.left +
				(values.length <= 1 ? plotWidth / 2 : (index / (values.length - 1)) * plotWidth);
			const y =
				padding.top + plotHeight - (Math.max(0, Math.min(value, safeMax)) / safeMax) * plotHeight;
			return `${x.toFixed(1)},${y.toFixed(1)}`;
		})
		.join(' ');
}
