import { isModuleStatus, worstStatus, type ModuleStatus } from '#lib/modules';

export type JsonObject = Record<string, unknown>;

export function asObject(value: unknown): JsonObject {
	return typeof value === 'object' && value !== null && !Array.isArray(value)
		? (value as JsonObject)
		: {};
}

export function asArray(value: unknown): unknown[] {
	return Array.isArray(value) ? value : [];
}

export function asNumber(value: unknown, fallback = 0): number {
	return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export function asOptionalNumber(value: unknown): number | null {
	return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function asString(value: unknown, fallback = '—'): string {
	return typeof value === 'string' && value.length > 0 ? value : fallback;
}

export function asStatus(value: unknown): ModuleStatus {
	return isModuleStatus(value) ? value : 'unknown';
}

export function moduleStatus(detail: JsonObject | null): ModuleStatus {
	return asStatus(detail?.status);
}

export function overallStatus(statuses: unknown[]): ModuleStatus {
	return worstStatus(statuses.map(asStatus));
}

export function usageTone(percent: number): ModuleStatus {
	if (percent >= 95) return 'critical';
	if (percent >= 85) return 'warn';
	return 'ok';
}
