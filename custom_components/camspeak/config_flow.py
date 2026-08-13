"""Config flow for camspeak integration."""

from typing import Any, override

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import voluptuous as vol

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import CONF_VERIFY_SSL, DEFAULT_PORT, DEFAULT_VERIFY_SSL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


def _build_base_url(host: str, port: int, verify_ssl: bool) -> str:
    """Build the base URL for the camspeak API."""
    scheme = "https" if verify_ssl else "http"
    return f"{scheme}://{host}:{port}"


async def _test_connection(hass: Any, host: str, port: int, verify_ssl: bool) -> bool:
    """Validate the connection by hitting the health endpoint."""
    base_url = _build_base_url(host, port, verify_ssl)
    client = CamspeakApiClient(
        base_url,
        session=aiohttp_client.async_get_clientsession(hass, verify_ssl=verify_ssl),
    )
    try:
        await client.health()
    except CamspeakApiClientError:
        return False
    return True


class CamspeakConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for camspeak."""

    VERSION = 1

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            verify_ssl = user_input[CONF_VERIFY_SSL]
            if await _test_connection(self.hass, host, port, verify_ssl):
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"camspeak ({host})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @override
    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port

        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # Try http first, then https
        for verify_ssl in (False, True):
            if await _test_connection(self.hass, host, port, verify_ssl):
                self._discovery_data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_VERIFY_SSL: verify_ssl,
                }
                self.context["title_placeholders"] = {"host": host}
                return await self.async_step_zeroconf_confirm()

        return self.async_abort(reason="cannot_connect")

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm zeroconf discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"camspeak ({self._discovery_data[CONF_HOST]})",
                data=self._discovery_data,
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._discovery_data[CONF_HOST]},
        )
