import { describe, expect, it } from 'vitest';

import { formatBytes, formatPercent, formatUptime } from './format';

describe('formatBytes', () => {
	it('formatea GB, MB y TB', () => {
		expect(formatBytes(11.4 * 1024 ** 3)).toBe('11.4 GB');
		expect(formatBytes(512 * 1024 ** 2)).toBe('512 MB');
		expect(formatBytes(2.5 * 1024 ** 4)).toBe('2.50 TB');
	});

	it('gestiona valores ausentes', () => {
		expect(formatBytes(null)).toBe('—');
		expect(formatBytes(Number.NaN)).toBe('—');
	});
});

describe('formatPercent', () => {
	it('redondea según los dígitos pedidos', () => {
		expect(formatPercent(23.456)).toBe('23%');
		expect(formatPercent(23.456, 1)).toBe('23.5%');
		expect(formatPercent(undefined)).toBe('—');
	});
});

describe('formatUptime', () => {
	it('muestra días, horas y minutos', () => {
		expect(formatUptime(4 * 86400 + 3 * 3600 + 12 * 60)).toBe('4d 3h 12m');
		expect(formatUptime(2 * 3600 + 5 * 60)).toBe('2h 5m');
		expect(formatUptime(42 * 60)).toBe('42m');
	});

	it('gestiona valores inválidos', () => {
		expect(formatUptime(-1)).toBe('—');
		expect(formatUptime(null)).toBe('—');
	});
});
