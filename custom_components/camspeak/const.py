"""Constants for the camspeak integration."""

import logging

DOMAIN = "camspeak"

LOGGER = logging.getLogger(__package__)

CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 8585
DEFAULT_VERIFY_SSL = True

PLAYBACK_IDLE = "idle"
PLAYBACK_PLAYING = "playing"
PLAYBACK_PAUSED = "paused"
