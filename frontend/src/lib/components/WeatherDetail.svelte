<script lang="ts">
	import { Droplets, Umbrella, Wind } from '@lucide/svelte';

	import { asArray, asNumber, asObject, asOptionalNumber, asString } from '#lib/detail';
	import { formatDate, formatDateTime, formatNumber, formatPercent, formatTime } from '#lib/format';
	import StatTile from './StatTile.svelte';
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
	const aqiCategory = $derived(asString(air.category, '—'));
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
	const dailyRows = $derived([...history.slice(-30), ...forecast]);

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

<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
	<StatTile
		label="Temperatura"
		value={temperature !== null ? `${formatNumber(temperature, 1)} °C` : '—'}
		hint={condition}
	/>
	<StatTile
		label="Sensación"
		value={apparent !== null ? `${formatNumber(apparent, 1)} °C` : '—'}
		hint="térmica"
	/>
	<StatTile
		label="Humedad"
		value={humidity !== null ? formatPercent(humidity, 0) : '—'}
		hint={todayMax !== null && todayMin !== null
			? `máx ${formatNumber(todayMax, 0)}° / mín ${formatNumber(todayMin, 0)}°`
			: null}
	/>
	<StatTile
		label="Calidad del aire"
		value={aqi !== null ? `${formatNumber(aqi, 0)} AQI` : '—'}
		hint={aqiCategory}
	/>
</div>

<div class="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-center gap-4">
			<span
				class="inline-flex h-16 w-16 items-center justify-center rounded-[18px] bg-surface-2 text-accent"
			>
				<WeatherIcon name={icon} size={40} />
			</span>
			<div>
				<p class="text-[13px] text-ink-3">{asString(location.name, 'Monterrey')}</p>
				<div class="flex items-baseline gap-2">
					<span class="text-[40px] leading-none font-semibold tracking-tight text-ink">
						{temperature !== null ? formatNumber(temperature, 1) : '—'}
					</span>
					<span class="text-[20px] font-medium text-ink-2">°C</span>
				</div>
				<p class="mt-1 text-[14px] font-medium text-ink-2">{condition}</p>
			</div>
		</div>

		<dl class="mt-5 grid gap-x-4 gap-y-3 border-t border-line pt-4 text-[13px] sm:grid-cols-3">
			<div>
				<dt class="text-ink-3">Máx / mín hoy</dt>
				<dd class="font-medium text-ink">
					{todayMax !== null ? `${formatNumber(todayMax, 1)}°` : '—'} /
					{todayMin !== null ? `${formatNumber(todayMin, 1)}°` : '—'}
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Viento</dt>
				<dd class="font-medium text-ink">
					{formatNumber(asOptionalNumber(current.wind_speed), 1)} km/h
					{#if asOptionalNumber(current.wind_gusts) !== null}
						<span class="text-[11px] text-ink-3">
							· rachas {formatNumber(asOptionalNumber(current.wind_gusts), 0)}
						</span>
					{/if}
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">Presión</dt>
				<dd class="font-medium text-ink">
					{formatNumber(asOptionalNumber(current.pressure), 0)} hPa
				</dd>
			</div>
			<div>
				<dt class="text-ink-3">UV</dt>
				<dd class="font-medium text-ink">{formatNumber(asOptionalNumber(current.uv_index), 1)}</dd>
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
		<p class="mt-3 text-[11px] text-ink-3">Actualizado {formatDateTime(updatedAt)}</p>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-start justify-between gap-3">
			<div>
				<h2 class="text-[17px] font-semibold text-ink">Lluvia</h2>
				<p class="mt-1 text-[13px] text-ink-2">
					{rainedToday ? 'Sí ha llovido hoy' : 'No ha llovido hoy'}
				</p>
			</div>
			<span
				class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium {rainedToday
					? 'bg-accent/10 text-accent'
					: 'bg-surface-2 text-ink-3'}"
			>
				{#if rainedToday}
					<Droplets size={14} aria-hidden="true" />
				{/if}
				{rainedToday ? 'Con lluvia' : 'Seco'}
			</span>
		</div>

		<div class="mt-5 grid grid-cols-2 gap-4">
			<div>
				<p class="text-[12px] text-ink-3">Hoy</p>
				<p class="tabular text-[24px] font-semibold text-ink">{formatNumber(todayMm, 1)} mm</p>
			</div>
			<div>
				<p class="text-[12px] text-ink-3">Últimas 24 h</p>
				<p class="tabular text-[24px] font-semibold text-ink">{formatNumber(last24hMm, 1)} mm</p>
			</div>
			<div>
				<p class="text-[12px] text-ink-3">Este mes</p>
				<p class="tabular text-[18px] font-semibold text-ink">{formatNumber(monthMm, 1)} mm</p>
				<p class="text-[11px] text-ink-3">{monthDays} días con lluvia</p>
			</div>
			<div>
				<p class="text-[12px] text-ink-3">Última lluvia</p>
				<p class="text-[15px] font-semibold text-ink">
					{lastRainDate ? formatDate(lastRainDate) : '—'}
				</p>
				<p class="text-[11px] text-ink-3">
					{#if lastRainMm !== null}
						{formatNumber(lastRainMm, 1)} mm
					{/if}
					{#if daysSinceRain !== null}
						· hace {daysSinceRain} día{daysSinceRain === 1 ? '' : 's'}
					{/if}
				</p>
			</div>
		</div>

		<div class="mt-4 flex items-center gap-2 border-t border-line pt-3 text-[12px] text-ink-3">
			<Umbrella size={15} aria-hidden="true" />
			<span>Horas de lluvia hoy: {asNumber(rain.today_hours)}</span>
			<Wind size={15} class="ml-auto" aria-hidden="true" />
			<span>{formatNumber(asOptionalNumber(current.wind_speed), 0)} km/h</span>
		</div>
	</div>
</div>

<div class="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-baseline justify-between gap-2">
			<h2 class="text-[17px] font-semibold text-ink">Calidad del aire</h2>
			<span class="text-[12px] text-ink-3">AQI US</span>
		</div>
		<div class="mt-4 flex items-end gap-3">
			<span class="tabular text-[34px] leading-none font-semibold {aqiTone(aqi)}">
				{aqi !== null ? formatNumber(aqi, 0) : '—'}
			</span>
			<span class="pb-1 text-[14px] font-medium {aqiTone(aqi)}">{aqiLabel(aqi)}</span>
		</div>
		<p class="mt-2 text-[12px] text-ink-3">
			{aqiCategory}
			{#if asOptionalNumber(air.european_aqi) !== null}
				· europeo {formatNumber(asOptionalNumber(air.european_aqi), 0)}
			{/if}
		</p>
		<div class="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-4 text-[12px]">
			{#each pollutants as pollutant}
				<div>
					<p class="text-ink-3">{pollutant.label}</p>
					<p class="tabular font-semibold text-ink">
						{pollutant.value !== null ? formatNumber(pollutant.value, 1) : '—'}
						<span class="text-[10px] font-normal text-ink-3">{pollutant.unit}</span>
					</p>
				</div>
			{/each}
		</div>
	</div>

	<div class="rounded-brand-lg border border-line bg-surface p-5">
		<div class="flex items-baseline justify-between gap-2">
			<h2 class="text-[17px] font-semibold text-ink">Próximas 24 horas</h2>
			<span class="text-[12px] text-ink-3">Open-Meteo</span>
		</div>
		<div class="mt-4 flex gap-2 overflow-x-auto pb-2">
			{#each hourly as hour (hour.at)}
				<div
					class="flex min-w-[92px] flex-col items-center gap-1.5 rounded-brand border border-line bg-surface-2/40 px-2 py-3 text-center"
				>
					<span class="text-[11px] text-ink-3">{formatTime(asString(hour.at, ''))}</span>
					<WeatherIcon name={asString(hour.icon, 'cloud')} size={22} />
					<span class="tabular text-[15px] font-semibold text-ink">
						{formatNumber(asOptionalNumber(hour.temperature), 0)}°
					</span>
					<span class="text-[11px] text-accent">
						{formatPercent(asOptionalNumber(hour.probability), 0)}
					</span>
					<span class="text-[10px] text-ink-3">
						AQI {hour.aqi !== null ? formatNumber(asOptionalNumber(hour.aqi), 0) : '—'}
					</span>
				</div>
			{/each}
		</div>
	</div>
</div>

<div class="rounded-brand-lg border border-line bg-surface p-5">
	<div class="flex flex-wrap items-baseline justify-between gap-2">
		<h2 class="text-[17px] font-semibold text-ink">Registro diario</h2>
		<span class="text-[12px] text-ink-3">
			últimos 30 días + próximos 7 · histórico persistente
		</span>
	</div>
	{#if dailyRows.length === 0}
		<p class="mt-4 text-[13px] text-ink-3">Todavía no hay registros diarios.</p>
	{:else}
		<div class="mt-4 overflow-x-auto">
			<table class="w-full min-w-[980px] border-collapse text-[12px]">
				<thead>
					<tr class="border-b border-line text-left text-[11px] tracking-wide text-ink-3 uppercase">
						<th class="pb-2 pr-4 font-medium">Día</th>
						<th class="pb-2 pr-4 font-medium">Condición</th>
						<th class="pb-2 pr-4 font-medium">Máx / mín</th>
						<th class="pb-2 pr-4 font-medium">Lluvia</th>
						<th class="pb-2 pr-4 font-medium">Humedad</th>
						<th class="pb-2 pr-4 font-medium">AQI máx</th>
						<th class="pb-2 font-medium">Sol</th>
					</tr>
				</thead>
				<tbody>
					{#each dailyRows as day (day.date)}
						{@const isToday = asString(day.date) === asString(today.date, '—')}
						{@const isForecast = day.forecast === true}
						<tr class="border-b border-line/60 last:border-0 {isToday ? 'bg-surface-2/40' : ''}">
							<td class="py-2.5 pr-4 font-medium text-ink">
								{formatDate(asString(day.date))}
								{#if isToday}
									<span class="ml-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] text-accent">
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
								{formatNumber(asOptionalNumber(day.temp_max), 1)}° /
								{formatNumber(asOptionalNumber(day.temp_min), 1)}°
							</td>
							<td
								class="tabular py-2.5 pr-4 {asNumber(day.precipitation_mm) > 0
									? 'text-accent'
									: 'text-ink-3'}"
							>
								{formatNumber(asOptionalNumber(day.precipitation_mm), 1)} mm
								{#if asOptionalNumber(day.precipitation_hours) !== null}
									<span class="text-[10px]"
										>· {formatNumber(asOptionalNumber(day.precipitation_hours), 0)} h</span
									>
								{/if}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{formatPercent(asOptionalNumber(day.humidity_avg), 0)}
							</td>
							<td class="tabular py-2.5 pr-4 text-ink-2">
								{day.aqi_max !== null ? formatNumber(asOptionalNumber(day.aqi_max), 0) : '—'}
							</td>
							<td class="py-2.5 text-[11px] text-ink-3">
								{formatTime(asString(day.sunrise, ''))} · {formatTime(asString(day.sunset, ''))}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
	<p class="mt-3 text-[12px] leading-5 text-ink-3">
		Datos actuales, hourly y previsión de Open-Meteo. El registro diario se guarda cada 15 minutos y
		se conserva hasta {asNumber(detail.history_days, 730)} días. La lluvia de hoy se calcula con las horas
		transcurridas; la previsión no se cuenta como lluvia real.
	</p>
</div>
