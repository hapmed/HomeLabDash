import { redirect } from '@sveltejs/kit';

import { sessionCookieName } from '#lib/server/backend';
import type { ModuleCard } from '#lib/modules';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, cookies }) => {
	let response: Response;
	try {
		response = await fetch('/api/v1/modules');
	} catch {
		return {
			modules: [] as ModuleCard[],
			unavailable: true,
			updatedAt: new Date().toISOString()
		};
	}

	if (response.status === 401) {
		cookies.delete(sessionCookieName(), { path: '/' });
		redirect(303, '/login');
	}

	if (!response.ok) {
		return {
			modules: [] as ModuleCard[],
			unavailable: true,
			updatedAt: new Date().toISOString()
		};
	}

	const modules = (await response.json()) as ModuleCard[];
	return { modules, unavailable: false, updatedAt: new Date().toISOString() };
};
