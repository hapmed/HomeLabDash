import { redirect } from '@sveltejs/kit';

import { sessionCookieName } from '#lib/server/backend';
import type { UserInfo } from '#lib/modules';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ fetch, cookies }) => {
	const response = await fetch('/api/v1/auth/me');
	if (response.status === 401) {
		cookies.delete(sessionCookieName(), { path: '/' });
		redirect(303, '/login');
	}
	if (!response.ok) {
		return { user: null as UserInfo | null };
	}
	const user = (await response.json()) as UserInfo;
	return { user };
};
