import { redirect } from '@sveltejs/kit';

import { sessionCookieName } from '#lib/server/backend';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ cookies }) => {
	cookies.delete(sessionCookieName(), { path: '/' });
	redirect(303, '/login');
};
