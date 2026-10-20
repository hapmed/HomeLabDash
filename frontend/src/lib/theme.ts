export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'hld-theme';

export function currentTheme(): Theme {
	return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

export function applyTheme(theme: Theme): void {
	document.documentElement.classList.toggle('dark', theme === 'dark');
	try {
		localStorage.setItem(STORAGE_KEY, theme);
	} catch {
		/* almacenamiento no disponible */
	}
}

export function toggleTheme(): Theme {
	const next: Theme = currentTheme() === 'dark' ? 'light' : 'dark';
	applyTheme(next);
	return next;
}
