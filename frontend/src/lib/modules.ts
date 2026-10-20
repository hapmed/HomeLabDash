export type ModuleStatus = 'ok' | 'warn' | 'critical' | 'unknown';

export interface ModuleSummary {
	label: string;
	value: string | number;
	unit?: string | null;
	detail?: string | null;
}

export interface ModuleCard {
	id: string;
	name: string;
	description: string;
	icon: string;
	order: number;
	enabled: boolean;
	status: ModuleStatus;
	summary: ModuleSummary;
	updated_at?: string | null;
}

export interface ModuleDetail extends ModuleCard {
	available: boolean;
	detail: Record<string, unknown> | null;
	error: string | null;
}

export interface AlertItem {
	id: string;
	module_id: string;
	severity: string;
	title: string;
	message: string;
	status: string;
	started_at: string;
}

export interface UserInfo {
	id: string;
	username: string;
	is_admin: boolean;
}

export const STATUS_META: Record<ModuleStatus, { label: string; tone: string }> = {
	ok: { label: 'Correcto', tone: 'text-success' },
	warn: { label: 'Atención', tone: 'text-warning' },
	critical: { label: 'Crítico', tone: 'text-danger' },
	unknown: { label: 'Sin datos', tone: 'text-ink-3' }
};

export function isModuleStatus(value: unknown): value is ModuleStatus {
	return value === 'ok' || value === 'warn' || value === 'critical' || value === 'unknown';
}

export function worstStatus(statuses: ModuleStatus[]): ModuleStatus {
	if (statuses.includes('critical')) return 'critical';
	if (statuses.includes('warn')) return 'warn';
	if (statuses.includes('unknown') || statuses.length === 0) return 'unknown';
	return 'ok';
}
