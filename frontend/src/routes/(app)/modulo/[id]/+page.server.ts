import { error, redirect } from '@sveltejs/kit';

import { sessionCookieName } from '#lib/server/backend';
import type { ModuleDetail } from '#lib/modules';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch, cookies }) => {
	let response: Response;
	try {
		response = await fetch(`/api/v1/modules/${encodeURIComponent(params.id)}`);
	} catch {
		error(503, 'Servicio no disponible');
	}

	if (response.status === 401) {
		cookies.delete(sessionCookieName(), { path: '/' });
		redirect(303, '/login');
	}

	if (response.status === 404) {
		error(404, 'Módulo no encontrado');
	}

	if (!response.ok) {
		error(503, 'No se pudo cargar el módulo');
	}

	const moduleDetail = (await response.json()) as ModuleDetail;
	return { module: moduleDetail, updatedAt: new Date().toISOString() };
};
