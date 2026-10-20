import { describe, expect, it } from 'vitest';

import { chartMax, chartPoints, niceCeil, parseHistory } from './internet';

describe('parseHistory', () => {
	it('normaliza las muestras y descarta las inválidas', () => {
		const history = parseHistory([
			{ at: '2026-10-20T10:00:00Z', download_mbps: 120.5, upload_mbps: 20, latency_ms: 12 },
			{ at: '', download_mbps: 1 },
			{ download_mbps: 2 },
			'basura'
		]);
		expect(history).toHaveLength(1);
		expect(history[0]).toMatchObject({ download_mbps: 120.5, upload_mbps: 20 });
	});

	it('tolera valores ausentes', () => {
		const history = parseHistory([{ at: '2026-10-20T10:00:00Z' }]);
		expect(history[0].download_mbps).toBeNull();
		expect(history[0].latency_ms).toBeNull();
	});
});

describe('niceCeil', () => {
	it('redondea al alza de forma legible', () => {
		expect(niceCeil(0)).toBe(1);
		expect(niceCeil(7)).toBe(10);
		expect(niceCeil(12)).toBe(20);
		expect(niceCeil(43)).toBe(50);
		expect(niceCeil(78)).toBe(100);
		expect(niceCeil(240)).toBe(500);
	});
});

describe('chartMax y chartPoints', () => {
	it('calcula el máximo de descarga y subida', () => {
		const samples = parseHistory([
			{ at: '2026-10-20T10:00:00Z', download_mbps: 120, upload_mbps: 30 },
			{ at: '2026-10-20T11:00:00Z', download_mbps: 240, upload_mbps: 40 }
		]);
		expect(chartMax(samples)).toBe(500);
	});

	it('genera un punto por muestra y respeta el padding', () => {
		const padding = { top: 10, right: 10, bottom: 10, left: 10 };
		const points = chartPoints([0, 100], 120, 120, 100, padding).split(' ');
		expect(points).toHaveLength(2);
		expect(points[0]).toBe('10.0,110.0');
		expect(points[1]).toBe('110.0,10.0');
	});
});
