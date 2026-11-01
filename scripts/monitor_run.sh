#!/bin/bash
# Log resource use of a running pipeline process every N seconds (macOS).
# Usage: scripts/monitor_run.sh <pattern in the command line> <output.csv> [interval_s]
# Example: scripts/monitor_run.sh jw07035 data/ngc602_resources.csv 10
# Columns: time, process memory (RSS, MB), process CPU (%), system-wide free memory (%), swap used (MB)
export LC_ALL=C   # decimal point instead of comma (German locale would break the CSV)
PATTERN="$1"; OUT="$2"; DT="${3:-10}"
PID=$(pgrep -f "astropipe.*${PATTERN}" | head -1)
if [ -z "$PID" ]; then echo "no running astropipe process matching '$PATTERN'"; exit 1; fi
echo "monitoring PID $PID -> $OUT (every ${DT}s, stops when the process ends)"
echo "time,rss_mb,cpu_pct,mem_free_pct,swap_used_mb" > "$OUT"
while kill -0 "$PID" 2>/dev/null; do
  rss=$(ps -o rss= -p "$PID" | tr -d ' ')
  cpu=$(ps -o %cpu= -p "$PID" | tr -d ' ')
  free=$(memory_pressure -Q 2>/dev/null | awk -F': ' '/percentage/{gsub("%","",$2); print $2}')
  swap=$(sysctl -n vm.swapusage | awk '{gsub("M","",$6); print $6}')
  echo "$(date +%H:%M:%S),$(( ${rss:-0} / 1024 )),$cpu,$free,$swap" >> "$OUT"
  sleep "$DT"
done
echo "process ended – $(($(wc -l < "$OUT") - 1)) samples in $OUT"
