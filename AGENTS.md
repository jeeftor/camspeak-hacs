# camspeak-hacs

Home Assistant custom integration for [camspeak](https://github.com/jeeftor/camspeak) — exposes cameras as media player entities and provides services for TTS, preset playback, streaming, and playback control.

> **Related repo**: [camspeak](https://github.com/jeeftor/camspeak) — the Go backend server this integration talks to via its REST API. The API is defined by camspeak's OpenAPI spec (`GET /api/openapi.json`). When the backend API changes, update `custom_components/camspeak/api.py` and `const.py` to match.

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
├── manifest.yaml      # HA integration manifest (domain, version, config_flow)
├── const.py           # API endpoint paths, service names, constants
├── api.py             # Async aiohttp client wrapping all REST endpoints
├── config_flow.py     # UI setup flow (enter host/port/SSL)
├── coordinator.py     # DataUpdateCoordinator — polls /api/cameras + /api/playback every 10s
├── __init__.py        # Entry point — sets up coordinator, platforms, and services
├── media_player.py    # MediaPlayerEntity per camera (play/pause/stop/source/volume)
├── sensor.py          # SensorEntity per camera (playback state + online status)
└── services.yaml      # Service schemas for HA UI
```

## Development

No build step — Python is interpreted by HA at runtime. To test:

1. Symlink or copy `custom_components/camspeak/` into your HA config's `custom_components/` directory
2. Restart HA
3. Add the integration via Settings → Devices & Services

### Key conventions

- **API client** (`api.py`): All HTTP calls go through `CamspeakApiClient`. When camspeak adds a new endpoint, add a method here and a constant in `const.py`.
- **Coordinator** (`coordinator.py`): Polls every 10 seconds. Returns a dict keyed by camera name, each containing camera info, playback state, and preset list.
- **Media player** (`media_player.py`): Maps camspeak playback state to HA `MediaPlayerState`. Presets appear as sources. Gain (0-10) maps to volume (0.0-1.0).
- **Services** (`__init__.py`): Registered in `_async_register_services`. Each service is a thin wrapper calling the API client.

### When the camspeak API changes

1. Check `GET /api/openapi.json` on the camspeak server for the current schema
2. Update `const.py` if endpoint paths changed
3. Update `api.py` — add/modify methods to match
4. Update `services.yaml` if service parameters changed
5. Update `media_player.py` or `sensor.py` if playback state shape changed
6. Bump `manifest.yaml` version

## HACS requirements

- `hacs.json` declares minimum HA version and HACS version
- `manifest.yaml` sets `integration_type: hub`, `config_flow: true`, and declares `zeroconf` discovery for `_camspeak._tcp.local.`
- Repo must have `README.md` and `LICENSE` (HACS validates these)

## Auto-discovery

camspeak advertises itself via mDNS as `_camspeak._tcp.local.` (see camspeak's `internal/discovery/` package). HA's built-in zeroconf scanner picks this up and triggers `async_step_zeroconf` in the config flow, which pre-fills the host and port from the mDNS TXT records. No manual entry needed — the user just clicks "Configure" on the discovered device.
