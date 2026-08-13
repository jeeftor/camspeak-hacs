"""Constants for the camspeak integration."""

DOMAIN = "camspeak"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_URL = "url"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 8585
DEFAULT_VERIFY_SSL = True

# API endpoints
API_CAMERAS = "/api/cameras"
API_PLAYBACK = "/api/playback"
API_LIBRARY = "/api/library"
API_VOICES = "/api/voices"
API_PLAY = "/api/play"
API_SPEAK = "/api/speak"
API_BROADCAST = "/api/broadcast"
API_PLAY_STREAM = "/api/play-stream"
API_PLAY_URL = "/api/play-url"
API_BEEP = "/api/beep"
API_STOP = "/api/stop"
API_PAUSE = "/api/pause"
API_RESUME = "/api/resume"
API_HEALTH = "/api/health"

# Playback states
PLAYBACK_IDLE = "idle"
PLAYBACK_PLAYING = "playing"
PLAYBACK_PAUSED = "paused"

# Service names
SERVICE_SPEAK = "speak"
SERVICE_PLAY_PRESET = "play_preset"
SERVICE_PLAY_STREAM = "play_stream"
SERVICE_PLAY_URL = "play_url"
SERVICE_BROADCAST = "broadcast"
SERVICE_BEEP = "beep"
SERVICE_STOP = "stop"
SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"

# Platforms
PLATFORM_SENSOR = "sensor"
PLATFORM_MEDIA_PLAYER = "media_player"
PLATFORMS = [PLATFORM_SENSOR, PLATFORM_MEDIA_PLAYER]
