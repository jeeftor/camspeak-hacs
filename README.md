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
- **Services** — speak, play_preset, play_stream, play_url, broadcast, beep, stop, pause, resume
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
  camera: backyard
  text: "Person detected at the door"
  voice: af_sky
  gain: 5.0
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

```yaml
# Text-to-speech (uses camspeak's Kokoro engine)
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

# Play an audio file (download + transcode + play)
action: camspeak.play_url
data:
  camera: backyard
  url: "https://example.com/alert.mp3"

# Stream a live URL or playlist
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
