const GIB = 1024 ** 3;
const MIB = 1024 ** 2;

export function formatBytes(bytes: number | null | undefined): string {
	if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) return '—';
	if (bytes >= GIB) return `${(bytes / GIB).toFixed(1)} GB`;
	if (bytes >= MIB) return `${(bytes / MIB).toFixed(0)} MB`;
	if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
	return `${Math.round(bytes)} B`;
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
	if (value === null || value === undefined || !Number.isFinite(value)) return '—';
	return `${value.toFixed(digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
	if (value === null || value === undefined || !Number.isFinite(value)) return '—';
	return value.toFixed(digits);
}

export function formatUptime(seconds: number | null | undefined): string {
	if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
		return '—';
	}
	const total = Math.floor(seconds);
	const days = Math.floor(total / 86400);
	const hours = Math.floor((total % 86400) / 3600);
	const minutes = Math.floor((total % 3600) / 60);
	if (days > 0) return `${days}d ${hours}h ${minutes}m`;
	if (hours > 0) return `${hours}h ${minutes}m`;
	return `${minutes}m`;
}

export function formatTime(value: Date | string | null | undefined): string {
	if (!value) return '—';
	const date = value instanceof Date ? value : new Date(value);
	if (Number.isNaN(date.getTime())) return '—';
	return new Intl.DateTimeFormat('es-ES', {
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit'
	}).format(date);
}

export function formatDateTime(value: Date | string | null | undefined): string {
	if (!value) return '—';
	const date = value instanceof Date ? value : new Date(value);
	if (Number.isNaN(date.getTime())) return '—';
	return new Intl.DateTimeFormat('es-ES', {
		dateStyle: 'medium',
		timeStyle: 'short'
	}).format(date);
}
