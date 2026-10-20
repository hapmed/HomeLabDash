import { describe, expect, it } from 'vitest';

import {
	asArray,
	asNumber,
	asObject,
	asStatus,
	asString,
	overallStatus,
	usageTone
} from './detail';

describe('detail helpers', () => {
	it('normaliza objetos, arrays y escalares', () => {
		expect(asObject({ a: 1 })).toEqual({ a: 1 });
		expect(asObject([1, 2])).toEqual({});
		expect(asArray([1, 2])).toEqual([1, 2]);
		expect(asArray('x')).toEqual([]);
		expect(asNumber('12', 7)).toBe(7);
		expect(asString('', 'x')).toBe('x');
	});

	it('normaliza estados', () => {
		expect(asStatus('critical')).toBe('critical');
		expect(asStatus('otro')).toBe('unknown');
		expect(overallStatus(['ok', 'warn'])).toBe('warn');
	});

	it('asigna tono según uso', () => {
		expect(usageTone(20)).toBe('ok');
		expect(usageTone(88)).toBe('warn');
		expect(usageTone(99)).toBe('critical');
	});
});
