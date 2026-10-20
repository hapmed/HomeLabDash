import type { AlertItem, ModuleCard, ModuleDetail } from '#lib/modules';
import type { HistorySample } from '#lib/history';

export class ApiError extends Error {
	constructor(
		public readonly status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try {
		response = await fetch(`/api/v1${path}`, {
			credentials: 'same-origin',
			headers: { accept: 'application/json', ...(init?.headers ?? {}) },
			...init
		});
	} catch {
		throw new ApiError(0, 'sin conexión con el servidor');
	}

	if (response.status === 401 && typeof window !== 'undefined') {
		window.location.assign('/login');
		throw new ApiError(401, 'sesión expirada');
	}

	if (!response.ok) {
		let detail = `error ${response.status}`;
		try {
			const body = (await response.json()) as { detail?: string };
			if (body.detail) detail = body.detail;
		} catch {
			/* respuesta sin JSON */
		}
		throw new ApiError(response.status, detail);
	}

	return (await response.json()) as T;
}

export const api = {
	modules: () => request<ModuleCard[]>('/modules'),
	module: (id: string) => request<ModuleDetail>(`/modules/${encodeURIComponent(id)}`),
	moduleHistory: (id: string, hours = 24) =>
		request<HistorySample[]>(
			`/modules/${encodeURIComponent(id)}/history?hours=${Math.max(1, Math.min(720, hours))}`
		),
	alerts: () => request<AlertItem[]>('/alerts'),
	dockerLogs: (id: string, tail = 100) =>
		request<{ container: string; id: string; lines: string[]; tail: number }>(
			`/modules/docker/containers/${encodeURIComponent(id)}/logs?tail=${tail}`
		)
};
