# larry-tracker

Tracks the location of Larry (a cat) via an AirTag, using
[FindMy.py](https://github.com/malmeloo/FindMy.py) to query Apple's FindMy
network, and renders the resulting path on an OpenStreetMap-based web UI.

## Architecture

Two containers:

- **proxy** (Caddy, `proxy/`) -- the only published service and the
  browser's single origin. It serves the static map page
  (`proxy/site/index.html`), generates `/config.js` with the CARTO key from
  its environment, forwards `/api/*` to location-service with the `/api`
  prefix stripped, and forwards `/ws` to location-service's WebSocket. See
  `proxy/Caddyfile`.
- **location-service** -- polls Apple's FindMy network on an interval,
  stores reports in SQLite, and exposes them over a small REST API
  (`GET /locations`, `GET /locations/latest`, `GET /trips`, plus point edits
  and deletes) and a `/ws` WebSocket that signals when data changes.

There is no UI backend: the page's JavaScript talks to location-service
through the proxy. location-service is not reachable from the host, only
through the proxy, so its unauthenticated edit/delete routes are not exposed
directly. It owns its SQLite database entirely.

By default it runs against a **mock** FindMy client (`FINDMY_MODE=mock`)
that simulates Larry wandering around, so the whole stack runs out of the
box with no Apple account.

## How trip detection works

Raw location reports are just a stream of timestamped points. `GET /trips`
turns that stream into discrete journeys. All of this logic lives in
`location-service/src/location_service/trips.py` and is unit-tested in
isolation from the DB/FindMy layers.

### 1. Quality filtering

Before anything else, a point is dropped if either:

- `confidence < MIN_CONFIDENCE` (default `1`) -- Apple's own confidence
  rating for the report.
- `horizontal_accuracy > MAX_HORIZONTAL_ACCURACY_METERS` (default `100`) --
  the report's estimated error radius, in meters.

This stops one noisy report from distorting a trip's shape or triggering a
false round-trip match.

### 2. Segmenting into trips (time-gap based)

Trips are split wherever the gap between two consecutive reports exceeds
`TRIP_GAP_MINUTES` (default `45`). For time-ordered points $p_0, \dots, p_n$:

$$
\text{split between } p_i \text{ and } p_{i+1} \iff t(p_{i+1}) - t(p_i) > \text{gap}
$$

This is deliberately not based on distance, and not on fixed clock windows
(e.g. "every 6 hours"):

- A fixed window can slice one continuous walk in half, or glue two
  unrelated ones together, purely by chance of when it happened to start.
- FindMy reports only arrive when the AirTag is near another Apple device,
  so an unusually long gap in reports is itself the signal that Larry left
  known network coverage -- a better proxy for "went on a trip" than raw
  distance, which is noisy and doesn't capture "left and came back" at all.

### 3. Round-trip detection (haversine distance)

If a home point is configured (`HOME_LATITUDE` / `HOME_LONGITUDE`), each
trip is labelled `is_round_trip`: whether its _last_ point falls within
`HOME_RADIUS_METERS` (default `75`) of home. Distance is computed with the
haversine formula for great-circle distance between two lat/lon points:

$$
\begin{aligned}
a &= \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right) \\
d &= 2R \cdot \arcsin\left(\sqrt{a}\right)
\end{aligned}
$$

where

- $\phi$ is the latitude (radians)
- $\lambda$ is the longitude (radians)
- $\Delta\phi$ and $\Delta\lambda$ are the delta between the two points
- $R$ is Earth's radius (6,371,000m)

Haversine is used instead of flat
Euclidean distance on the raw lat/lon degrees because lines of longitude
converge towards the poles --
a given number of degrees of longitude covers less real-world distance the
further from the equator you are, so naive Euclidean distance would
under/overestimate "near home" depending on latitude.

Without a configured home point, `is_round_trip` is always `null` for every
trip -- it's a label derived from the segmentation above, never a rule the
segmentation itself depends on.

## Running locally

The map uses CARTO's dark basemap, which requires a free API key (CARTO
stopped serving keyless tiles in 2026). Get one instantly, no approval
queue, at https://carto.com/basemaps/apikey (free up to 5 million tile
loads/month), then set it in `.env` next to `docker-compose.yml`:

```
CARTO_API_KEY=<your key>
```

This key ends up visible in the page's source -- that's expected, it's a
rate-limit/quota identifier CARTO's own client-side usage model relies on,
not a secret -- but keep it out of git by leaving it in the gitignored
`.env` rather than committing it anywhere.

```shell
docker compose up --build
```

- UI: http://localhost:8000
- location-service API, through the proxy: http://localhost:8000/api/
  (e.g. http://localhost:8000/api/trips)

A plain `docker compose up` runs the code baked into the images. For
development, use watch mode instead (`make dev`, or
`docker compose up --build --watch`), driven by the `develop.watch` rules in
`docker-compose.yml`:

- The map page (`proxy/site/`) is synced into the proxy; a browser reload
  picks up the change.
- `proxy/Caddyfile` changes are synced and Caddy restarts.
- location-service Python source changes are synced and the service
  restarts; `pyproject.toml` / `uv.lock` changes rebuild its image.

`make smoke` checks every route of a running stack. Run `make help` for the
other shortcuts (`prod`, `down`, `logs`, `test`, `lint`, `fmt`).

## Switching to a real AirTag

1. Get Larry's AirTag private key as base64 (see FindMy.py's docs/examples
   for exporting accessory keys).
2. Log in to the Apple account once, locally (2FA can't be done headlessly
   inside a container):

   ```shell
   cd location-service
   uv sync
   uv run scripts/login.py
   ```

   This writes `../data/account.json` (and `ani_libs.bin`), which
   location-service mounts and reuses.

3. Set in your environment (or an `.env` file next to `docker-compose.yml`):

   ```
   FINDMY_MODE=live
   FINDMY_AIRTAG_KEY_B64=<Larry's key>
   ```

4. `docker compose up --build`.

location-service re-saves the account session after every poll, so it keeps
working without re-triggering 2FA until Apple invalidates the session.

## Development

location-service is a standalone `uv` project:

```shell
cd location-service
uv sync
uv run pytest
```

The map page is a single static file, `proxy/site/index.html`, served by
Caddy; there is nothing to build or install for it.
