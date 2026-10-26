# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tracks Larry (a cat) via an AirTag. Two Docker containers:

- `location-service/` -- a Python `uv` project. Polls Apple's FindMy network
  (via [FindMy.py](https://github.com/malmeloo/FindMy.py)) on an interval,
  stores reports in its own SQLite DB, and exposes them over a REST API plus
  a `/ws` change signal. Not published to the host.
- `proxy/` -- Caddy, the only published service and the browser's single
  origin. It serves the static map page (`proxy/site/index.html`, Leaflet +
  MapLibre), generates `/config.js` with the CARTO key from its environment,
  and forwards `/api/*` (prefix stripped) and `/ws` to location-service. See
  `proxy/Caddyfile`. There is no UI backend: the page's JavaScript talks to
  location-service through the proxy.

See `README.md` for the full setup/usage story (mock vs. live mode, the
interactive login flow for a real Apple account).

## Commands

Python work happens in location-service (`cd location-service` first):

```shell
uv sync          # install deps (reads uv.lock)
uv run pytest    # run that service's tests
uv run ruff check .
uv run ruff format .
```

Run the whole stack: `docker compose up --build` from the repo root, or
`make dev` for watch mode. Only the proxy is published, on port 8000: the UI
at `/`, location-service's API at `/api/*`. `make smoke` checks every route
of a running stack (`scripts/smoke.sh`); the page itself has no unit tests.

## Architecture notes

**`findmy_client.py` is the integration seam.** `location_service` never
touches FindMy.py's `LocationReport` objects directly -- `RealFindMyClient`
adapts them into our own `LocationPoint` dataclass immediately, and
`MockFindMyClient` (`mock_findmy.py`) produces the same `LocationPoint` shape
by simulating a random walk. `build_client(settings)` picks between them
based on `FINDMY_MODE` (`mock` by default, `live` for a real Apple account).
Everything downstream of that boundary (`db.py`, `poller.py`, `main.py`) is
identical in both modes. When extending this, keep new FindMy.py-specific
logic inside `findmy_client.py` rather than letting its types leak further.

**Apple auth can't be done headlessly.** 2FA requires an interactive
prompt, so login happens out-of-band via `location-service/scripts/login.py`
run locally (not in Docker), producing `data/account.json`. The running
service only ever restores that saved session (`AsyncAppleAccount.from_json`)
and re-saves it after each poll -- if `account.json` is missing in live mode,
`RealFindMyClient` raises rather than attempting an interactive login. Note
that `AppleAccount`/`AsyncAppleAccount`'s `to_json`/`from_json` are
synchronous methods even though most of the rest of the async API is not --
easy to accidentally `await` them.

**`data/` is the shared runtime volume**, mounted into location-service
only: the SQLite DB, `account.json` (Apple session -- sensitive), and
`ani_libs.bin` (anisette provisioning data) all live there. It's
gitignored; never commit its contents.

**location-service's Dockerfile uses `uv.lock`** for reproducible installs
-- regenerate with `uv lock` after changing its `pyproject.toml`, and commit
the lockfile. The proxy image (`proxy/Dockerfile`) just copies the Caddyfile
and `proxy/site/` into the official Caddy image.
