import { defineEnvVars } from '@sveltejs/kit/env';

/**
 * Variables de entorno explícitas del servidor SvelteKit.
 * Se acceden con `import { ... } from '$app/env/private'`.
 * No son públicas: nunca llegan al navegador.
 */
export const variables = defineEnvVars({
	BACKEND_URL: {
		public: false,
		static: false,
		description: 'URL interna del backend FastAPI',
		schema: (value: string | undefined) => value ?? 'http://api:8000'
	},
	COOKIE_NAME: {
		public: false,
		static: false,
		description: 'Nombre de la cookie de sesión',
		schema: (value: string | undefined) => value ?? 'hld_session'
	},
	COOKIE_SECURE: {
		public: false,
		static: false,
		description: 'Cookie de sesión solo por HTTPS',
		schema: (value: string | undefined) => (value ?? 'true') !== 'false'
	}
});
