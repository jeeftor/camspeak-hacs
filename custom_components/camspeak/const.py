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
# v4.0.0 removed MQTT rules engine — HA automations are now the way to
# trigger camspeak actions. v3.1.2 added centralized gain resolution.
MIN_APP_VERSION = (4, 0, 0)
