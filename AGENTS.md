# camspeak-hacs

Home Assistant custom integration for [camspeak](https://github.com/jeeftor/camspeak) — exposes cameras as media player entities and provides services for TTS, preset playback, streaming, and playback control.

> **Related repo**: `../camspeak` (sibling checkout) — [camspeak](https://github.com/jeeftor/camspeak) Go backend server. The API is defined by camspeak's OpenAPI spec (`GET /api/openapi.json`). When the backend API changes, update `custom_components/camspeak/api.py` to match.
>
> Tests are run against the sibling `../ha/core` Home Assistant checkout (its `tests.common` and `homeassistant` package are required).

## Architecture

This is a Python integration installed via HACS. It does **not** contain any Go code — it's a thin async HTTP client wrapping camspeak's REST endpoints.

```
Home Assistant ──(aiohttp)──> camspeak REST API (/api/*)
                                   │
                           ┌───────┴────────┐
                           │ media_player.py │  play/pause/stop/source/volume
                           │ sensor.py       │  playback state + online status
                           │ __init__.py     │  services: speak, play_preset, etc.
                           └─────────────────┘
```

## File layout

```
custom_components/camspeak/
├── manifest.json      # HA integration manifest (domain, version, config_flow, zeroconf)
├── const.py           # Constants + LOGGER
├── api.py             # Async aiohttp client wrapping all REST endpoints
├── config_flow.py     # UI setup flow + zeroconf discovery (host/port/SSL)
├── coordinator.py     # DataUpdateCoordinator — polls /api/cameras + /api/playback every 10s
├── __init__.py        # Entry point — sets up coordinator, platforms, and services
├── entity.py          # Base entity class (device info, unique ID pattern)
├── media_player.py    # MediaPlayerEntity per camera (play/pause/stop/source/volume)
├── sensor.py          # SensorEntity per camera (playback state + online status)
├── diagnostics.py     # Diagnostics support for troubleshooting
├── services.yaml      # Service schemas for HA UI
└── strings.json       # Config flow translations
```

## Development

### Linting

```bash
ruff check custom_components/ tests/
ruff format custom_components/ tests/
codespell custom_components/ tests/ README.md --ignore-words-list=hass
yamllint custom_components/camspeak/services.yaml
```

Or install pre-commit hooks:

```bash
pre-commit install
```

### Testing

Tests use HA's test framework. The `tests/` tree here is not a self-contained package — it imports `tests.common` and the `homeassistant` package from the sibling `../ha/core` checkout. To run locally:

```bash
# 1. Temporarily link this repo's tests into the HA core tree:
ln -s /home/jstein/devel/camspeak-hacs/tests/components/camspeak /home/jstein/devel/ha/core/tests/components/camspeak

# 2. Run from the HA core checkout with this repo on PYTHONPATH (so `custom_components/camspeak` resolves):
cd /home/jstein/devel/ha/core
PYTHONPATH=/home/jstein/devel/camspeak-hacs /home/jstein/devel/ha/core/.venv/bin/python -m pytest tests/components/camspeak/ -v

# 3. Remove the symlink when done:
rm /home/jstein/devel/ha/core/tests/components/camspeak
```

### Manual testing

1. Symlink or copy `custom_components/camspeak/` into your HA config's `custom_components/` directory
2. Restart HA
3. Add the integration via Settings → Devices & Services

### Key conventions

- **API client** (`api.py`): All HTTP calls go through `CamspeakApiClient`. When camspeak adds a new endpoint, add a method here.
- **Coordinator** (`coordinator.py`): Polls every 10 seconds. Returns `CamspeakData` with per-camera `CameraData` (camera info, playback state, preset list).
- **Media player** (`media_player.py`): Maps camspeak playback state to HA `MediaPlayerState`. Presets appear as sources. Gain (0-10) maps to volume (0.0-1.0). It implements `async_browse_media` so camspeak library presets appear in HA's media browser, and `async_play_media` resolves `media-source://` URIs and auto-routes URLs to `play_url` (download + transcode) or `play_stream` (live streams / `.m3u` / `.pls`).
- **Services** (`__init__.py`): Registered in `_async_register_services`. Each service is a thin wrapper calling the API client. Services are removed on unload.
- **Entity** (`entity.py`): Base class with `CoordinatorEntity`, device info, and unique ID pattern.

### When the camspeak API changes

1. Check `GET /api/openapi.json` on the camspeak server for the current schema
2. Update `api.py` — add/modify methods to match
3. Update `services.yaml` if service parameters changed
4. Update `media_player.py` or `sensor.py` if playback state shape changed
5. Bump `manifest.json` version

## HACS requirements

- `hacs.json` declares minimum HA version and HACS version
- `manifest.json` sets `integration_type: hub`, `config_flow: true`, and declares `zeroconf` discovery for `_camspeak._tcp.local.`
- Repo must have `README.md` and `LICENSE` (HACS validates these)

## Auto-discovery

camspeak advertises itself via mDNS as `_camspeak._tcp.local.` (see camspeak's `internal/discovery/` package). HA's built-in zeroconf scanner picks this up and triggers `async_step_zeroconf` in the config flow, which pre-fills the host and port from the mDNS TXT records. No manual entry needed — the user just clicks "Configure" on the discovered device.
