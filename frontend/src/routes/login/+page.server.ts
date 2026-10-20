import { fail, redirect } from '@sveltejs/kit';

import { backendUrl, sessionCookieName, sessionCookieSecure } from '#lib/server/backend';
import type { Actions } from './$types';

interface LoginResponse {
	access_token: string;
	expires_in: number;
}

export const actions: Actions = {
	default: async ({ request, fetch, cookies, url }) => {
		const form = await request.formData();
		const username = String(form.get('username') ?? '').trim();
		const password = String(form.get('password') ?? '');

		if (!username || !password) {
			return fail(400, { username, error: 'Introduce usuario y contraseña.' });
		}

		let response: Response;
		try {
			response = await fetch(`${backendUrl()}/api/v1/auth/login`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ username, password })
			});
		} catch {
			return fail(503, {
				username,
				error: 'No se puede contactar con el servidor. Inténtalo de nuevo.'
			});
		}

		if (response.status === 429) {
			return fail(429, {
				username,
				error: 'Demasiados intentos. Espera un minuto antes de volver a probar.'
			});
		}

		if (!response.ok) {
			return fail(401, { username, error: 'Usuario o contraseña incorrectos.' });
		}

		const body = (await response.json()) as LoginResponse;
		cookies.set(sessionCookieName(), body.access_token, {
			path: '/',
			httpOnly: true,
			sameSite: 'lax',
			secure: sessionCookieSecure(),
			maxAge: body.expires_in
		});

		const next = url.searchParams.get('next');
		redirect(303, next && next.startsWith('/') && !next.startsWith('//') ? next : '/');
	}
};
