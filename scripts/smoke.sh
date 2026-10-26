#!/bin/bash
#
# Smoke-check a running stack through the proxy: the static page, its
# generated config, and the routes forwarded to location-service.
#
# Usage: scripts/smoke.sh [base-url]   (default http://localhost:8000)

set -euo pipefail

base="${1:-http://localhost:8000}"
failures=0

check() {
  local name="$1" path="$2" expect="$3"
  local body
  if ! body="$(curl -fsS --max-time 5 "${base}${path}")"; then
    echo "FAIL ${name}: ${path} did not return 2xx" >&2
    failures=$((failures + 1))
    return
  fi
  if [[ ${body} != *"${expect}"* ]]; then
    echo "FAIL ${name}: ${path} response does not contain '${expect}'" >&2
    failures=$((failures + 1))
    return
  fi
  echo "ok   ${name}"
}

check "page" "/" "leaflet"
check "page config" "/config.js" "cartoApiKey"
check "proxy health" "/healthz" '"ok"'
check "location-service health" "/api/healthz" '"ok"'
check "trips" "/api/trips" '"trips"'

cache_control="$(curl -fsS --max-time 5 -o /dev/null -D - "${base}/" | tr -d '\r' | awk -F': ' 'tolower($1) == "cache-control" {print $2}')"
if [[ ${cache_control} == "no-store" ]]; then
  echo "ok   page is never cached"
else
  echo "FAIL page cache-control is '${cache_control}', expected 'no-store'" >&2
  failures=$((failures + 1))
fi

if [[ ${failures} -gt 0 ]]; then
  echo "${failures} check(s) failed" >&2
  exit 1
fi
