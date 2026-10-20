/* HomeLabDash — service worker del shell.
 * No cachea /api/* (respuestas autenticadas). Offline muestra una página
 * estática; el dashboard necesita red para datos en vivo.
 */
const CACHE = 'homelabdash-shell-v1';
const SHELL = [
	'/offline.html',
	'/manifest.webmanifest',
	'/brand/favicon-64.png',
	'/brand/apple-touch-icon.png',
	'/brand/icon-192.png',
	'/brand/icon-512.png'
];

self.addEventListener('install', (event) => {
	event.waitUntil(
		caches
			.open(CACHE)
			.then((cache) => cache.addAll(SHELL))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) =>
				Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
			)
			.then(() => self.clients.claim())
	);
});

self.addEventListener('fetch', (event) => {
	const request = event.request;
	if (request.method !== 'GET') return;

	const url = new URL(request.url);
	if (url.origin !== self.location.origin) return;

	// Nunca cachear API autenticada.
	if (url.pathname.startsWith('/api/')) return;

	if (request.mode === 'navigate') {
		event.respondWith(fetch(request).catch(() => caches.match('/offline.html')));
		return;
	}

	if (url.pathname.startsWith('/_app/') || url.pathname.startsWith('/brand/')) {
		event.respondWith(
			caches.match(request).then(
				(cached) =>
					cached ||
					fetch(request).then((response) => {
						if (response.ok) {
							const copy = response.clone();
							caches.open(CACHE).then((cache) => cache.put(request, copy));
						}
						return response;
					})
			)
		);
	}
});
