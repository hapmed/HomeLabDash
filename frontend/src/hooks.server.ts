import { BACKEND_URL, COOKIE_NAME } from '$app/env/private';
import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit/hooks';

const PUBLIC_PREFIXES = [
	'/login',
	'/_app',
	'/brand',
	'/icons',
	'/favicon',
	'/robots.txt',
	'/manifest.webmanifest',
	'/sw.js',
	'/offline.html'
];

const SECURITY_HEADERS: Record<string, string> = {
	'x-content-type-options': 'nosniff',
	'x-frame-options': 'DENY',
	'referrer-policy': 'strict-origin-when-cross-origin',
	'permissions-policy': 'camera=(), microphone=(), geolocation=()'
};

function isPublic(path: string): boolean {
	return PUBLIC_PREFIXES.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));
}

async function proxyApi(event: Parameters<Handle>[0]['event']): Promise<Response> {
	const target = `${BACKEND_URL}${event.url.pathname}${event.url.search}`;
	const headers = new Headers(event.request.headers);
	headers.delete('host');
	headers.delete('connection');
	headers.set('x-forwarded-for', event.getClientAddress());

	const init: RequestInit = { method: event.request.method, headers };
	if (!['GET', 'HEAD'].includes(event.request.method)) {
		init.body = await event.request.arrayBuffer();
	}

	let upstream: Response;
	try {
		upstream = await fetch(target, init);
	} catch {
		return new Response(JSON.stringify({ detail: 'servicio no disponible' }), {
			status: 503,
			headers: { 'content-type': 'application/json' }
		});
	}

	const responseHeaders = new Headers(upstream.headers);
	responseHeaders.delete('content-encoding');
	responseHeaders.delete('content-length');
	responseHeaders.delete('transfer-encoding');
	return new Response(upstream.body, {
		status: upstream.status,
		statusText: upstream.statusText,
		headers: responseHeaders
	});
}

export const handle: Handle = async ({ event, resolve }) => {
	const path = event.url.pathname;

	if (path.startsWith('/api/')) {
		const response = await proxyApi(event);
		for (const [key, value] of Object.entries(SECURITY_HEADERS)) response.headers.set(key, value);
		return response;
	}

	if (!isPublic(path) && !event.cookies.get(COOKIE_NAME)) {
		redirect(303, `/login?next=${encodeURIComponent(path)}`);
	}

	const response = await resolve(event);
	for (const [key, value] of Object.entries(SECURITY_HEADERS)) response.headers.set(key, value);
	return response;
};
