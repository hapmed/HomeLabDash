import { BACKEND_URL, COOKIE_NAME, COOKIE_SECURE } from '$app/env/private';

export function backendUrl(): string {
	return BACKEND_URL;
}

export function sessionCookieName(): string {
	return COOKIE_NAME;
}

export function sessionCookieSecure(): boolean {
	return COOKIE_SECURE;
}
