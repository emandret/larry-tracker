# larry-tracker

Tracks the location of Larry (a cat) via an AirTag, using
[FindMy.py](https://github.com/malmeloo/FindMy.py) to query Apple's FindMy
network, and renders the resulting path on an OpenStreetMap-based web UI.

## Architecture

Two containers:

- **location-service** -- polls Apple's FindMy network on an interval,
  stores reports in SQLite, and exposes them over a small REST API
  (`GET /locations`, `GET /locations/latest`, `GET /trips`).
- **ui-service** -- calls location-service and renders the path on a
  Leaflet/OpenStreetMap map.

They communicate over HTTP (not a shared DB file), so location-service owns
its SQLite database entirely.

By default both run against a **mock** FindMy client (`FINDMY_MODE=mock`)
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
a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)
$$

$$
d = 2R \cdot \arcsin\left(\sqrt{a}\right)
$$

where $\phi$ is latitude, $\lambda$ is longitude (both in radians),
$\Delta\phi$/$\Delta\lambda$ are the differences between the two points,
and $R$ is Earth's radius (6,371,000m). Haversine is used instead of flat
Euclidean distance on the raw lat/lon degrees because lines of longitude
converge towards the poles --
a given number of degrees of longitude covers less real-world distance the
further from the equator you are, so naive Euclidean distance would
under/overestimate "near home" depending on latitude.

Without a configured home point, `is_round_trip` is always `null` for every
trip -- it's a label derived from the segmentation above, never a rule the
segmentation itself depends on.

## Running locally

```shell
docker compose up --build
```

- UI: http://localhost:8000
- location-service API: http://localhost:8001

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

Each service is a standalone `uv` project:

```shell
cd location-service   # or ui-service
uv sync
uv run pytest
```
