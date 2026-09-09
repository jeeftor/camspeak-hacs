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
# v3.1.2 added centralized gain resolution and fixed Describe ignoring
# request-level gain; v3.1.0 added VU meters for one-shot playback;
# v3.0.0 refactored config/benchmark/vision playground.
MIN_APP_VERSION = (3, 1, 2)
