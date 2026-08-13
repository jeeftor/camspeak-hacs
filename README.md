<p align="center">
  <img src="assets/camspeak-mark.svg" alt="camspeak" width="120">
</p>

# Camspeak Home Assistant Integration

[![hacs](https://img.shields.io/badge/HACS-Default-orange)](https://github.com/hacs/integration)

Home Assistant custom integration for [camspeak](https://github.com/jeeftor/camspeak) — the camera audio router that streams TTS and audio to IP camera speakers.

## Features

- **Media Player entities** for each camera — play presets, pause/resume/stop streams, select source from preset library
- **Sensors** — playback state and camera online status
- **Services** — speak, play_preset, play_stream, play_url, broadcast, beep, stop, pause, resume
- **Config flow** — set up via UI, no YAML required

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
3. Enter your camspeak server host and port (e.g. `192.168.1.50` and `8585`)
4. Click **Submit**

## Usage

### Media Player

Each camera appears as a media player entity (`media_player.backyard_speaker`). You can:

- **Play a preset** — select from the source dropdown (populated from your camspeak library)
- **Pause/Resume** — works on live streams and looped presets
- **Stop** — stops all audio on the camera
- **Volume** — maps to camspeak's gain (0-10)

### Services

```yaml
# Text-to-speech
action: camspeak.speak
data:
  camera: backyard
  text: "Person detected at the door"
  voice: af_sky

# Play a preset
action: camspeak.play_preset
data:
  camera: backyard
  preset: person_detected
  category: alerts

# Play a preset in a loop (pausable)
action: camspeak.play_preset
data:
  camera: backyard
  preset: scary_sounds
  loop: true

# Stream a live URL
action: camspeak.play_stream
data:
  camera: backyard
  url: "http://stream.example.com:8000/live"

# Pause/resume/stop
action: camspeak.pause
data:
  camera: backyard

action: camspeak.resume
data:
  camera: backyard

action: camspeak.stop
data:
  camera: backyard

# Broadcast to all cameras
action: camspeak.broadcast
data:
  text: "Attention all cameras"
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
      camera: backyard
      preset: here-comes-the-rain-again
```

## Requirements

- A running camspeak server (see [camspeak](https://github.com/jeeftor/camspeak))
- Home Assistant 2024.1.0 or newer

## License

MIT
