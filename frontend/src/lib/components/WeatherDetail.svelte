<script lang="ts">
	import { Droplets, Wind } from '@lucide/svelte';

	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatDate, formatDateTime, formatNumber, formatPercent, formatTime } from '#lib/format';
	import WeatherIcon from './WeatherIcon.svelte';

	let { detail }: { detail: Record<string, unknown> } = $props();

	const current = $derived(asObject(detail.current));
	const today = $derived(asObject(detail.today));
	const forecast = $derived(asArray(detail.forecast).map(asObject));
	const history = $derived(asArray(detail.history).map(asObject));
	const hourly = $derived(asArray(detail.hourly).map(asObject));
	const air = $derived(asObject(detail.air));
	const rain = $derived(asObject(detail.rain));
	const alerts = $derived(asArray(detail.alerts).map((item) => asString(item, '')));
	const location = $derived(asObject(detail.location));
	const updatedAt = $derived(asString(detail.updated_at, ''));
	const temperature = $derived(asOptionalNumber(current.temperature));
	const apparent = $derived(asOptionalNumber(current.apparent_temperature));
	const humidity = $derived(asOptionalNumber(current.humidity));
	const condition = $derived(asString(current.condition, 'Sin datos'));
	const icon = $derived(asString(current.icon, 'cloud'));
	const aqi = $derived(asOptionalNumber(air.us_aqi));
	const europeanAqi = $derived(asOptionalNumber(air.european_aqi));
	const rainedToday = $derived(rain.rained_today === true);
	const todayMm = $derived(asNumber(rain.today_mm, 0));
	const last24hMm = $derived(asNumber(rain.last_24h_mm, 0));
	const monthMm = $derived(asNumber(rain.month_mm, 0));
	const monthDays = $derived(asNumber(rain.month_days, 0));
	const lastRainDate = $derived(asString(rain.last_rain_date, ''));
	const lastRainMm = $derived(asOptionalNumber(rain.last_rain_mm));
	const daysSinceRain = $derived(asOptionalNumber(rain.days_since_rain));
	const todayMax = $derived(asOptionalNumber(today.temp_max));
	const todayMin = $derived(asOptionalNumber(today.temp_min));
	const recentDays = $derived([...history.slice(-7), ...forecast]);
	const olderDays = $derived(history.slice(0, -7).slice(-30));
	const nextHours = $derived(hourly.slice(0, 12));
	const laterHours = $derived(hourly.slice(12));

	const pollutants = $derived([
		{ label: 'PM2.5', value: asOptionalNumber(air.pm2_5), unit: 'µg/m³' },
		{ label: 'PM10', value: asOptionalNumber(air.pm10), unit: 'µg/m³' },
		{ label: 'Ozono', value: asOptionalNumber(air.ozone), unit: 'µg/m³' },
		{ label: 'NO₂', value: asOptionalNumber(air.no2), unit: 'µg/m³' },
		{ label: 'SO₂', value: asOptionalNumber(air.so2), unit: 'µg/m³' },
		{ label: 'CO', value: asOptionalNumber(air.co), unit: 'µg/m³' }
	]);

	function aqiTone(value: number | null): string {
		if (value === null) return 'text-ink-3';
		if (value <= 50) return 'text-success';
		if (value <= 100) return 'text-warning';
		return 'text-danger';
	}

	function aqiBar(value: number | null): string {
		if (value === null) return '0%';
		return `${Math.max(2, Math.min(100, (value / 300) * 100))}%`;
	}

	function aqiBarTone(value: number | null): string {
		if (value === null) return 'bg-ink-3/40';
		if (value <= 50) return 'bg-success';
		if (value <= 100) return 'bg-warning';
		return 'bg-danger';
	}

	function aqiLabel(value: number | null): string {
		if (value === null) return 'Sin datos';
		if (value <= 50) return 'Buena';
		if (value <= 100) return 'Moderada';
		if (value <= 150) return 'Mala para sensibles';
		if (value <= 200) return 'Mala';
		if (value <= 300) return 'Muy mala';
		return 'Peligrosa';
	}
</script>

{#snippet dayCard(day: Record<string, unknown>)}
	{@const isToday = asString(day.date) === asString(today.date, '—')}
	{@const isForecast = day.forecast === true}
	<div class="rounded-brand border border-line bg-surface-2/30 p-3">
		<div class="flex items-center justify-between gap-2">
			<div class="flex items-center gap-1.5">
				<span class="text-[13px] font-medium text-ink">{formatDate(asString(day.date))}</span>
				{#if isToday}
					<span class="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] text-accent">Hoy</span>
				{:else if isForecast}
					<span class="text-[10px] text-ink-3">pronóstico</span>
				{/if}
			</div>
			<span class="inline-flex items-center gap-1 text-[12px] text-ink-2">
				<WeatherIcon name={asString(day.icon, 'cloud')} size={15} />
				{asString(day.condition)}
			</span>
		</div>
		<div class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
			<div class="flex justify-between gap-2">
				<span class="text-ink-3">Máx / mín</span>
				<span class="font-medium text-ink">
					{formatNumber(asOptionalNumber(day.temp_max), 0)}° /
					{formatNumber(asOptionalNumber(day.temp_min), 0)}°
				</span>
			</div>
			<div class="flex justify-between gap-2">
				<span class="text-ink-3">Lluvia</span>
				<span
					class="font-medium {asNumber(day.precipitation_mm) > 0 ? 'text-accent' : 'text-ink-3'}"
				>
					{formatNumber(asOptionalNumber(day.precipitation_mm), 1)} mm
				</span>
			</div>
			<div class="flex justify-between gap-2">
				<span class="text-ink-3">Humedad</span>
				<span class="font-medium text-ink">
					{formatPercent(asOptionalNumber(day.humidity_avg), 0)}
				</span>
			</div>
			<div class="flex justify-between gap-2">
				<span class="text-ink-3">AQI máx</span>
				<span class="font-medium text-ink">
					{day.aqi_max !== null ? formatNumber(asOptionalNumber(day.aqi_max), 0) : '—'}
				</span>
			</div>
		</div>
	</div>
{/snippet}

{#if alerts.length > 0}
	<div
		role="status"
		class="rounded-brand-lg border border-warning/30 bg-warning/10 px-4 py-3 text-[13px] text-ink"
	>
		<p class="font-medium">Avisos meteorológicos</p>
		<ul class="mt-1 list-inside list-disc text-ink-2">
			{#each alerts as alert}
				<li>{alert}</li>
			{/each}
		</ul>
	</div>
{/if}

<div class="rounded-brand-lg border border-line bg-surface p-6">
	<div class="flex flex-wrap items-start gap-x-6 gap-y-5">
		<div class="flex items-center gap-4">
			<span
				class="inline-flex h-20 w-20 shrink-0 items-center justify-center rounded-[22px] bg-surface-2 text-accent"
			>
				<WeatherIcon name={icon} size={46} />
			</span>
			<div>
				<p class="text-[13px] text-ink-3">
					{asString(location.name, 'Monterrey')} · observación {formatTime(updatedAt)}
				</p>
				<div class="flex flex-wrap items-baseline gap-2">
					<span class="text-[52px] leading-none font-semibold tracking-tight text-ink">
						{temperature !== null ? formatNumber(temperature, 1) : '—'}
					</span>
					<span class="text-[24px] font-medium text-ink-2">°C</span>
					<span class="ml-1 text-[15px] font-medium text-ink-2">{condition}</span>
				</div>
				<p class="mt-1.5 text-[13px] text-ink-2">
					Sensación {apparent !== null ? `${formatNumber(apparent, 1)} °C` : '—'} · Máx
					{todayMax !== null ? `${formatNumber(todayMax, 0)}°` : '—'} / Mín
					{todayMin !== null ? `${formatNumber(todayMin, 0)}°` : '—'}
				</p>
			</div>
		</div>

		<dl class="ml-auto grid grid-cols-2 gap-x-6 gap-y-3 text-[13px] sm:grid-cols-3">
			<div>
				<dt class="text-ink-3">Humedad</dt>
				<dd class="font-medium text-ink">{formatPercent(humidity, 0)}</dd>
			</div>
			<div>
				<dt class="text-ink-3">Viento</dt>
				<dd class="font-medium text-ink">
					{formatNumber(asOptionalNumber(current.wind_speed), 0)} km/h
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">UV</dt>
				<dd class="font-medium text-ink">{formatNumber(asOptionalNumber(current.uv_index), 1)}</dd>
			</div>
			<div>
				<dt class="text-ink-3">Presión</dt>
				<dd class="font-medium text-ink">
					{formatNumber(asOptionalNumber(current.pressure), 0)} hPa
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Nubosidad</dt>
				<dd class="font-medium text-ink">
					{formatPercent(asOptionalNumber(current.cloud_cover), 0)}
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Sol</dt>
				<dd class="font-medium text-ink">
					{formatTime(asString(today.sunrise, ''))} · {formatTime(asString(today.sunset, ''))}
				</dd>
			</div>
		</dl>
	</div>
</div>

<div class="grid gap-4 lg:grid-cols-2">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-start justify-between gap-3">
			<h2 class="text-[17px] font-semibold text-ink">Lluvia</h2>
			<span
				class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium {rainedToday
					? 'bg-accent/10 text-accent'
					: 'bg-surface-2 text-ink-3'}"
			>
				{#if rainedToday}<Droplets size={14} aria-hidden="true" />{/if}
				{rainedToday ? 'Ha llovido' : 'Sin lluvia'}
			</span>
		</div>

		<p class="mt-4 text-[14px] text-ink-2">
			{rainedToday ? 'Sí ha llovido hoy.' : 'No ha llovido hoy.'}
		</p>
		<div class="mt-2 flex items-baseline gap-2">
			<span class="tabular text-[36px] leading-none font-semibold text-ink">
				{formatNumber(todayMm, 1)}
			</span>
			<span class="text-[14px] text-ink-2">mm hoy</span>
		</div>

		<dl class="mt-4 grid grid-cols-3 gap-3 border-t border-line pt-4 text-[13px]">
			<div>
				<dt class="text-ink-3">Última lluvia</dt>
				<dd class="mt-0.5 font-medium text-ink">
					{lastRainDate ? formatDate(lastRainDate) : '—'}
				</dd>
				<dd class="text-[11px] text-ink-3">
					{lastRainMm !== null ? `${formatNumber(lastRainMm, 1)} mm` : ''}
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Días sin llover</dt>
				<dd class="mt-0.5 font-medium text-ink">
					{daysSinceRain !== null ? daysSinceRain : '—'}
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Este mes</dt>
				<dd class="mt-0.5 font-medium text-ink">{formatNumber(monthMm, 1)} mm</dd>
				<dd class="text-[11px] text-ink-3">{monthDays} días</dd>
			</div>
		</dl>

		<p class="mt-3 text-[11px] text-ink-3">
			Últimas 24 h: {formatNumber(last24hMm, 1)} mm · {asNumber(rain.today_hours)} h de lluvia hoy
		</p>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-start justify-between gap-3">
			<h2 class="text-[17px] font-semibold text-ink">Calidad del aire</h2>
			<span class="text-[12px] text-ink-3">AQI US</span>
		</div>

		<div class="mt-4 flex items-end gap-3">
			<span class="tabular text-[36px] leading-none font-semibold {aqiTone(aqi)}">
				{aqi !== null ? formatNumber(aqi, 0) : '—'}
			</span>
			<span class="pb-1 text-[14px] font-medium {aqiTone(aqi)}">{aqiLabel(aqi)}</span>
		</div>
		<div class="mt-3 h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
			<div class="h-full rounded-full {aqiBarTone(aqi)}" style:width={aqiBar(aqi)}></div>
		</div>
		<p class="mt-2 text-[12px] text-ink-3">
			{#if europeanAqi !== null}Europeo {formatNumber(europeanAqi, 0)}{:else}Sin dato europeo{/if}
		</p>

		<details class="mt-4 border-t border-line pt-3">
			<summary class="cursor-pointer text-[12px] font-medium text-ink-3">Ver contaminantes</summary>
			<div class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[12px] sm:grid-cols-3">
				{#each pollutants as pollutant}
					<div>
						<span class="text-ink-3">{pollutant.label}</span>
						<span class="tabular ml-1 font-medium text-ink">
							{pollutant.value !== null ? formatNumber(pollutant.value, 1) : '—'}
						</span>
						<span class="text-[10px] text-ink-3">{pollutant.unit}</span>
					</div>
				{/each}
			</div>
		</details>
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Próximas 12 horas</h2>
		<span class="text-[12px] text-ink-3">Open-Meteo</span>
	</div>
	<div class="mt-4 flex gap-2 overflow-x-auto pb-2">
		{#each nextHours as hour (hour.at)}
			<div
				class="flex min-w-[76px] flex-col items-center gap-1 rounded-brand border border-line bg-surface-2/40 px-2 py-2.5 text-center"
			>
				<span class="text-[11px] text-ink-3">{formatTime(asString(hour.at, ''))}</span>
				<WeatherIcon name={asString(hour.icon, 'cloud')} size={20} />
				<span class="tabular text-[15px] font-semibold text-ink">
					{formatNumber(asOptionalNumber(hour.temperature), 0)}°
				</span>
				<span class="text-[10px] text-accent">
					{formatPercent(asOptionalNumber(hour.probability), 0)}
				</span>
			</div>
		{/each}
	</div>

	{#if laterHours.length > 0}
		<details class="mt-2">
			<summary class="cursor-pointer text-[12px] font-medium text-ink-3">
				Ver las 24 horas completas
			</summary>
			<div class="mt-3 flex gap-2 overflow-x-auto pb-2">
				{#each laterHours as hour (hour.at)}
					<div
						class="flex min-w-[76px] flex-col items-center gap-1 rounded-brand border border-line bg-surface-2/40 px-2 py-2.5 text-center"
					>
						<span class="text-[11px] text-ink-3">{formatTime(asString(hour.at, ''))}</span>
						<WeatherIcon name={asString(hour.icon, 'cloud')} size={20} />
						<span class="tabular text-[15px] font-semibold text-ink">
							{formatNumber(asOptionalNumber(hour.temperature), 0)}°
						</span>
						<span class="text-[10px] text-accent">
							{formatPercent(asOptionalNumber(hour.probability), 0)}
						</span>
					</div>
				{/each}
			</div>
		</details>
	{/if}
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Registro diario</h2>
		<span class="text-[12px] text-ink-3">últimos 7 días + previsión</span>
	</div>

	{#if recentDays.length === 0}
		<p class="mt-4 text-[13px] text-ink-3">Todavía no hay registros diarios.</p>
	{:else}
		<div class="mt-4">
			<div class="space-y-2 sm:hidden">
				{#each recentDays as day (day.date)}
					{@render dayCard(day)}
				{/each}
			</div>
			<div class="hidden overflow-x-auto sm:block">
				<table class="w-full min-w-[720px] border-collapse text-[12px]">
					<thead>
						<tr
							class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
						>
							<th class="pb-2 pr-4 font-medium">Día</th>
							<th class="pb-2 pr-4 font-medium">Condición</th>
							<th class="pb-2 pr-4 font-medium">Máx / mín</th>
							<th class="pb-2 pr-4 font-medium">Lluvia</th>
							<th class="pb-2 pr-4 font-medium">Humedad</th>
							<th class="pb-2 font-medium">AQI máx</th>
						</tr>
					</thead>
					<tbody>
						{#each recentDays as day (day.date)}
							{@const isToday = asString(day.date) === asString(today.date, '—')}
							{@const isForecast = day.forecast === true}
							<tr class="border-b border-line/60 last:border-0 {isToday ? 'bg-surface-2/40' : ''}">
								<td class="py-2.5 pr-4 font-medium text-ink">
									{formatDate(asString(day.date))}
									{#if isToday}
										<span
											class="ml-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] text-accent"
										>
											Hoy
										</span>
									{:else if isForecast}
										<span class="ml-1 text-[10px] text-ink-3">pronóstico</span>
									{/if}
								</td>
								<td class="py-2.5 pr-4 text-ink-2">
									<span class="inline-flex items-center gap-1.5">
										<WeatherIcon name={asString(day.icon, 'cloud')} size={16} />
										{asString(day.condition)}
									</span>
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatNumber(asOptionalNumber(day.temp_max), 0)}° /
									{formatNumber(asOptionalNumber(day.temp_min), 0)}°
								</td>
								<td
									class="tabular py-2.5 pr-4 {asNumber(day.precipitation_mm) > 0
										? 'text-accent'
										: 'text-ink-3'}"
								>
									{formatNumber(asOptionalNumber(day.precipitation_mm), 1)} mm
								</td>
								<td class="tabular py-2.5 pr-4 text-ink-2">
									{formatPercent(asOptionalNumber(day.humidity_avg), 0)}
								</td>
								<td class="tabular py-2.5 text-ink-2">
									{day.aqi_max !== null ? formatNumber(asOptionalNumber(day.aqi_max), 0) : '—'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}

	{#if olderDays.length > 0}
		<details class="mt-3">
			<summary class="cursor-pointer text-[12px] font-medium text-ink-3">
				Ver histórico de 30 días
			</summary>
			<div class="mt-3">
				<div class="space-y-2 sm:hidden">
					{#each olderDays as day (day.date)}
						{@render dayCard(day)}
					{/each}
				</div>
				<div class="hidden overflow-x-auto sm:block">
					<table class="w-full min-w-[720px] border-collapse text-[12px]">
						<thead>
							<tr
								class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase"
							>
								<th class="pb-2 pr-4 font-medium">Día</th>
								<th class="pb-2 pr-4 font-medium">Condición</th>
								<th class="pb-2 pr-4 font-medium">Máx / mín</th>
								<th class="pb-2 pr-4 font-medium">Lluvia</th>
								<th class="pb-2 pr-4 font-medium">Humedad</th>
								<th class="pb-2 font-medium">AQI máx</th>
							</tr>
						</thead>
						<tbody>
							{#each olderDays as day (day.date)}
								<tr class="border-b border-line/60 last:border-0">
									<td class="py-2.5 pr-4 font-medium text-ink">{formatDate(asString(day.date))}</td>
									<td class="py-2.5 pr-4 text-ink-2">
										<span class="inline-flex items-center gap-1.5">
											<WeatherIcon name={asString(day.icon, 'cloud')} size={16} />
											{asString(day.condition)}
										</span>
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">
										{formatNumber(asOptionalNumber(day.temp_max), 0)}° /
										{formatNumber(asOptionalNumber(day.temp_min), 0)}°
									</td>
									<td
										class="tabular py-2.5 pr-4 {asNumber(day.precipitation_mm) > 0
											? 'text-accent'
											: 'text-ink-3'}"
									>
										{formatNumber(asOptionalNumber(day.precipitation_mm), 1)} mm
									</td>
									<td class="tabular py-2.5 pr-4 text-ink-2">
										{formatPercent(asOptionalNumber(day.humidity_avg), 0)}
									</td>
									<td class="tabular py-2.5 text-ink-2">
										{day.aqi_max !== null ? formatNumber(asOptionalNumber(day.aqi_max), 0) : '—'}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		</details>
	{/if}

	<p class="mt-3 text-[12px] leading-5 text-ink-3">
		Datos actuales, hourly y previsión de Open-Meteo. El registro diario se guarda cada 15 minutos y
		se conserva hasta {asNumber(detail.history_days, 730)} días. La lluvia de hoy se calcula con las horas
		transcurridas; la previsión no se cuenta como lluvia real.
	</p>
</div>
