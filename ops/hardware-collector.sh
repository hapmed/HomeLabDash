#!/bin/sh
# Colector de SMART para HomeLabDash (se ejecuta en el host, como root).
# Escribe un JSON atómico que el agente lee en modo solo lectura.
set -eu

OUT_DIR="${HLD_DATA_DIR:-/opt/apps/HomeLabDash/data}"
SMARTCTL="${SMARTCTL:-/usr/sbin/smartctl}"

if [ ! -x "$SMARTCTL" ]; then
	echo "smartctl no está instalado en $SMARTCTL" >&2
	exit 1
fi

mkdir -p "$OUT_DIR"
TMP="$(mktemp "$OUT_DIR/.smart.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

{
	printf '{"generated_at":"%s","devices":{' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	first=1
	for device in /dev/nvme?n? /dev/sd? /dev/mmcblk?; do
		[ -b "$device" ] || continue
		name="${device#/dev/}"
		payload="$("$SMARTCTL" -j -a "$device" 2>/dev/null || true)"
		[ -n "$payload" ] || continue
		if [ "$first" -eq 0 ]; then
			printf ','
		fi
		first=0
		printf '"%s":%s' "$name" "$payload"
	done
	printf '}}'
} > "$TMP"

# No publicar un archivo corrupto si smartctl cambió de formato.
python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$TMP"
chmod 644 "$TMP"
mv "$TMP" "$OUT_DIR/smart.json"
trap - EXIT
