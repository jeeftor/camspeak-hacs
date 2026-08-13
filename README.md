<p align="center">
  <img src="assets/camspeak-mark.svg" alt="camspeak" width="120">
</p>

# Camspeak Home Assistant Integration

[![hacs](https://img.shields.io/badge/HACS-Default-orange)](https://github.com/hacs/integration)

Home Assistant custom integration for [camspeak](https://github.com/jeeftor/camspeak) — the camera audio router that streams TTS and audio to IP camera speakers.

## Features

- **Media Player entities** for each camera — play presets, pause/resume/stop, volume control
- **Binary sensors** — camera online/offline status
- **Sensors** — playback state (idle/playing/paused)
- **Smart services** with entity selectors, response data, and validation:
  - `speak` — TTS with voice dropdown, returns timing data
  - `play_preset` — play from library, supports loop
  - `play_stream` — live stream or playlist
  - `play_url` — download + transcode + play any audio file
  - `broadcast` — TTS or preset to all cameras, returns succeeded list
  - `beep` — test tone
  - `stop` / `pause` / `resume` — per-camera or all cameras
- **Real-time updates** via SSE — playback state updates instantly, no polling lag
- **Zeroconf discovery** — camspeak servers on your network are auto-discovered
- **Config flow** — set up via UI with a single URL, no YAML required

## Installation

### Via HACS

1. In HACS, go to **Integrations → Custom Repositories**
2. Add `https://github.com/jeeftor/camspeak-hacs` as type **Integration**
3. Click **Install** on "Camspeak"
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/camspeak/` folder to your HA `custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "Camspeak"
3. Enter your camspeak server URL (e.g. `http://192.168.1.50:8585` or `https://camspeak.example.com`)
4. Click **Submit**

If your camspeak server is on the same network and advertising via mDNS, it will be discovered automatically — just click **Configure** on the discovered device.

## Usage

### Media Player

Each camera appears as a media player entity (`media_player.backyard_speaker`). You can:

- **Play a preset** — select from the source dropdown (populated from your camspeak library)
- **Play custom audio** — use `media_player.play_media` with `media_content_type: url` to play any audio file, or `stream` for live streams
- **Pause/Resume** — works on live streams and looped presets
- **Stop** — stops all audio on the camera
- **Volume** — maps to camspeak's gain (0-10)

### Text-to-Speech

Camspeak has its own TTS engine (Kokoro, OpenAI-compatible). Use the `camspeak.speak` service to send TTS directly — it's a single API call that generates and plays audio on the camera:

```yaml
action: camspeak.speak
data:
  entity_id: media_player.backyard_speaker
  text: "Person detected at the door"
  voice: af_sky
  gain: 5.0
```

The `voice` field is a dropdown in the UI (af_sky, am_adam, etc.). Leave it empty to use the default voice configured in camspeak.

The service returns timing data when called with `return_response: true`:

```yaml
action: camspeak.speak
data:
  entity_id: media_player.backyard_speaker
  text: "Hello world"
return_response: true
```

Returns:
```json
{
  "cameras": {
    "backyard": {
      "status": "ok",
      "ttfs_ms": 200,
      "total_ms": 500,
      "timings": {"tts_ms": 1991, "transcode_ms": 50, "send_playback_ms": 1305}
    }
  }
}
```

You can also use HA's native TTS engines (Google, Piper, etc.) and pipe the result to camspeak via `play_media`:

```yaml
action: media_player.play_media
data:
  entity_id: media_player.backyard_speaker
  media_content_type: url
  media_content_id: "https://example.com/generated-tts.mp3"
```

### Services

All per-camera services use entity selectors — in the UI you'll get a dropdown of your cameras. You can also target by device, area, or label.

```yaml
# Text-to-speech (Kokoro engine, voice dropdown in UI)
action: camspeak.speak
data:
  entity_id: media_player.backyard_speaker
  text: "Person detected at the door"
  voice: af_sky

# Play a preset (from your camspeak library)
action: camspeak.play_preset
data:
  entity_id: media_player.backyard_speaker
  preset: dog
  category: alerts

# Play a preset in a loop (pausable)
action: camspeak.play_preset
data:
  entity_id: media_player.backyard_speaker
  preset: scary-laughing
  loop: true

# Play an audio file (download + transcode + play)
action: camspeak.play_url
data:
  entity_id: media_player.backyard_speaker
  url: "https://example.com/alert.mp3"

# Stream a live URL or playlist
action: camspeak.play_stream
data:
  entity_id: media_player.backyard_speaker
  url: "http://stream.example.com:8000/live"

# Broadcast to all cameras (returns which cameras succeeded)
action: camspeak.broadcast
data:
  text: "Attention all cameras"
return_response: true

# Test beep
action: camspeak.beep
data:
  entity_id: media_player.backyard_speaker

# Stop/pause/resume (entity_id optional — omit for all cameras)
action: camspeak.stop
data:
  entity_id: media_player.backyard_speaker

# Stop all cameras
action: camspeak.stop
```

### Targeting Multiple Cameras

Services accept HA's standard target selectors. You can target by entity, device, area, or label:

```yaml
# Target all cameras in an area
action: camspeak.speak
data:
  area_id: backyard
  text: "Motion detected"

# Target multiple cameras
action: camspeak.speak
data:
  entity_id:
    - media_player.backyard_speaker
    - media_player.frontyard_speaker
  text: "Alert"
```

### Example Automation

Play a rain sound when precipitation starts during daylight:

```yaml
triggers:
  - trigger: event
    event_type: weatherflowudp_precipitation_start
conditions:
  - condition: state
    entity_id: sun.sun
    state: above_horizon
actions:
  - service: camspeak.play_preset
    data:
      entity_id: media_player.backyard_speaker
      preset: here-comes-the-rain-again-rain-storm-weather-pour-lightning-thubder-flood
```

Speak when a person is detected:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.front_door_person
    to: "on"
actions:
  - service: camspeak.speak
    data:
      entity_id: media_player.frontyard_speaker
      text: "Person detected at the front door"
      voice: am_adam
```

## Requirements

- A running camspeak server (see [camspeak](https://github.com/jeeftor/camspeak))
- Home Assistant 2024.1.0 or newer

## License

MIT
