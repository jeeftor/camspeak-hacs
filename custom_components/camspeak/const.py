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
# v2.18.0 added stream reconnection, ICY metadata in playback detail,
# and dynaudnorm live-stream normalization.
MIN_APP_VERSION = (2, 18, 0)
