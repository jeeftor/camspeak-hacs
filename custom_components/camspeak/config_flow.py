"""Config flow for camspeak integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import DEFAULT_PORT, DEFAULT_VERIFY_SSL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _test_connection(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by hitting the health endpoint."""
    scheme = "https" if data.get(CONF_VERIFY_SSL, True) else "http"
    base_url = f"{scheme}://{data[CONF_HOST]}:{data[CONF_PORT]}"
    client = CamspeakApiClient(base_url, verify_ssl=data[CONF_VERIFY_SSL])
    try:
        health = await client.health()
        await client.close()
        return health
    except (CamspeakApiClientError, aiohttp.ClientError) as err:
        await client.close()
        raise CamspeakApiClientError(str(err)) from err


class CamspeakConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for camspeak."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            await _test_connection(self.hass, user_input)
        except CamspeakApiClientError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            errors["base"] = "unknown"
        else:
            title = f"camspeak ({user_input[CONF_HOST]})"
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery — pre-fill host/port from mDNS."""
        host = discovery_info.host
        port = discovery_info.port
        properties = discovery_info.properties

        # Extract version from TXT records if present
        version = properties.get(b"version", b"").decode() if b"version" in properties else ""

        # Build the data dict
        data = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_VERIFY_SSL: False,  # local discovery → default to http
        }

        # Check if already configured
        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # Try to validate the connection
        try:
            await _test_connection(self.hass, data)
        except (CamspeakApiClientError, aiohttp.ClientError):
            # Connection failed — try with SSL
            data[CONF_VERIFY_SSL] = True
            try:
                await _test_connection(self.hass, data)
            except (CamspeakApiClientError, aiohttp.ClientError):
                # Still failed — let the user fix it manually
                return await self.async_step_user()

        title = f"camspeak ({host})"
        self.context["title_placeholders"] = {"name": title}
        return self.async_create_entry(title=title, data=data)
