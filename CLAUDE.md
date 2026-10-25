# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tracks Larry (a cat) via an AirTag. Two independently-deployable Python
services, each its own `uv` project, run as separate Docker containers and
talk to each other over HTTP (not a shared DB file):

- `location-service/` -- polls Apple's FindMy network (via
  [FindMy.py](https://github.com/malmeloo/FindMy.py)) on an interval, stores
  reports in its own SQLite DB, and exposes them over a REST API.
- `ui-service/` -- calls location-service's API and renders the path on a
  Leaflet/OpenStreetMap map. Holds no persistent state of its own.

See `README.md` for the full setup/usage story (mock vs. live mode, the
interactive login flow for a real Apple account).

## Commands

Each service is developed independently (`cd location-service` or
`cd ui-service` first):

```shell
uv sync          # install deps (reads uv.lock)
uv run pytest    # run that service's tests
uv run ruff check .
uv run ruff format .
```

Run the whole stack: `docker compose up --build` from the repo root (ports
8000 for the UI, 8001 for location-service's API).

There is no root-level build/test command -- the two services have no shared
dependencies or tooling.

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

**Dockerfiles use `uv.lock`** (copied from each service directory) for
reproducible installs -- regenerate with `uv lock` after changing a
`pyproject.toml`, and commit the lockfile.
