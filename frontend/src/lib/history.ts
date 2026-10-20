export interface HistorySample {
	at: string | null;
	status: string;
	metrics: Record<string, number>;
}

export interface HistoryMetric {
	key: string;
	label: string;
	unit?: string;
	color: string;
	format?: 'percent' | 'bytes' | 'mbps' | 'celsius' | 'number' | 'money' | 'rpm' | 'bps';
}

export const HISTORY_METRICS: Record<string, HistoryMetric[]> = {
	overview: [
		{
			key: 'cpu_percent',
			label: 'CPU',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		},
		{
			key: 'memory_percent',
			label: 'Memoria',
			unit: '%',
			color: 'var(--color-accent-2)',
			format: 'percent'
		},
		{
			key: 'disk_percent',
			label: 'Disco raíz',
			unit: '%',
			color: 'var(--color-warning)',
			format: 'percent'
		}
	],
	cpu: [
		{
			key: 'percent',
			label: 'Uso de CPU',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		},
		{ key: 'load1', label: 'Carga 1m', color: 'var(--color-accent-2)', format: 'number' }
	],
	memory: [
		{ key: 'percent', label: 'RAM', unit: '%', color: 'var(--color-accent)', format: 'percent' },
		{
			key: 'swap_percent',
			label: 'Swap',
			unit: '%',
			color: 'var(--color-warning)',
			format: 'percent'
		}
	],
	storage: [
		{
			key: 'percent',
			label: 'Disco raíz',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		}
	],
	docker: [
		{
			key: 'running',
			label: 'Contenedores activos',
			color: 'var(--color-success)',
			format: 'number'
		},
		{
			key: 'cpu_percent',
			label: 'CPU de Docker',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		},
		{
			key: 'memory_used',
			label: 'RAM de Docker',
			color: 'var(--color-accent-2)',
			format: 'bytes'
		}
	],
	internet: [
		{
			key: 'download_mbps',
			label: 'Bajada',
			unit: 'Mbps',
			color: 'var(--color-accent)',
			format: 'mbps'
		},
		{
			key: 'upload_mbps',
			label: 'Subida',
			unit: 'Mbps',
			color: 'var(--color-accent-2)',
			format: 'mbps'
		},
		{
			key: 'latency_ms',
			label: 'Latencia',
			unit: 'ms',
			color: 'var(--color-warning)',
			format: 'number'
		}
	],
	devices: [
		{
			key: 'online',
			label: 'Dispositivos en línea',
			color: 'var(--color-success)',
			format: 'number'
		},
		{ key: 'total', label: 'Conocidos', color: 'var(--color-ink-3)', format: 'number' }
	],
	weather: [
		{
			key: 'temperature',
			label: 'Temperatura',
			unit: '°C',
			color: 'var(--color-warning)',
			format: 'celsius'
		},
		{
			key: 'humidity',
			label: 'Humedad',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		},
		{
			key: 'aqi',
			label: 'Calidad del aire (AQI)',
			color: 'var(--color-accent-2)',
			format: 'number'
		}
	],
	opencode: [
		{
			key: 'cpu_percent',
			label: 'CPU',
			unit: '%',
			color: 'var(--color-accent)',
			format: 'percent'
		},
		{
			key: 'memory_used',
			label: 'RAM',
			color: 'var(--color-accent-2)',
			format: 'bytes'
		},
		{ key: 'sessions', label: 'Sesiones', color: 'var(--color-success)', format: 'number' },
		{
			key: 'cost',
			label: 'Coste acumulado',
			unit: 'USD',
			color: 'var(--color-warning)',
			format: 'money'
		}
	],
	database: [
		{ key: 'size_bytes', label: 'Tamaño', color: 'var(--color-accent)', format: 'bytes' },
		{ key: 'connections', label: 'Conexiones', color: 'var(--color-accent-2)', format: 'number' },
		{
			key: 'cache_hit_ratio',
			label: 'Caché',
			unit: '%',
			color: 'var(--color-success)',
			format: 'percent'
		}
	],
	network: [
		{
			key: 'rx_bps',
			label: 'Recepción',
			unit: 'Mbps',
			color: 'var(--color-accent)',
			format: 'bps'
		},
		{ key: 'tx_bps', label: 'Envío', unit: 'Mbps', color: 'var(--color-accent-2)', format: 'bps' }
	],
	temperature: [
		{
			key: 'max_c',
			label: 'Máxima',
			unit: '°C',
			color: 'var(--color-warning)',
			format: 'celsius'
		},
		{ key: 'sensors', label: 'Sensores', color: 'var(--color-ink-3)', format: 'number' }
	],
	hardware: [
		{
			key: 'battery_percent',
			label: 'Batería',
			unit: '%',
			color: 'var(--color-success)',
			format: 'percent'
		},
		{
			key: 'root_inodes_percent',
			label: 'Inodos raíz',
			unit: '%',
			color: 'var(--color-warning)',
			format: 'percent'
		}
	]
};
