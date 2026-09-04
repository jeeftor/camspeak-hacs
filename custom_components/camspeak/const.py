"""Constants for the camspeak integration."""

import logging

DOMAIN = "camspeak"

LOGGER = logging.getLogger(__package__)

CONF_URL = "url"
CONF_VERIFY_SSL = "verify_ssl"

PLAYBACK_IDLE = "idle"
PLAYBACK_PLAYING = "playing"
PLAYBACK_PAUSED = "paused"

# Minimum camspeak app version required by this integration.
# v2.17.0 added /api/stream-levels and the level field on PlaybackState.
MIN_APP_VERSION = (2, 17, 0)
