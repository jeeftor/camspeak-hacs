"""Constants for the camspeak integration."""

import logging

DOMAIN = "camspeak"

LOGGER = logging.getLogger(__package__)

CONF_URL = "url"
CONF_VERIFY_SSL = "verify_ssl"

PLAYBACK_IDLE = "idle"
PLAYBACK_PREPARING = "preparing"
PLAYBACK_PLAYING = "playing"
PLAYBACK_PAUSED = "paused"

# Minimum camspeak app version required by this integration.
# v4.1.0 adds preparation/capability reporting and preserves omitted camera gain.
MIN_APP_VERSION = (4, 1, 0)
