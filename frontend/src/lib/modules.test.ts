import { describe, expect, it } from 'vitest';

import { worstStatus } from './modules';

describe('worstStatus', () => {
	it('prioriza critical', () => {
		expect(worstStatus(['ok', 'warn', 'critical'])).toBe('critical');
	});

	it('prioriza warn sobre ok', () => {
		expect(worstStatus(['ok', 'warn'])).toBe('warn');
	});

	it('devuelve unknown sin datos', () => {
		expect(worstStatus([])).toBe('unknown');
		expect(worstStatus(['ok', 'unknown'])).toBe('unknown');
	});

	it('devuelve ok si todo está bien', () => {
		expect(worstStatus(['ok', 'ok'])).toBe('ok');
	});
});
