"""Config flow for camspeak integration."""

from typing import Any, override

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import voluptuous as vol

from .api import CamspeakApiClient, CamspeakApiClientError
from .const import CONF_URL, CONF_VERIFY_SSL, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _parse_url(url: str) -> str:
    """Normalize the URL by stripping trailing slash."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    return url.rstrip("/")


async def _test_connection(hass: Any, url: str, verify_ssl: bool) -> bool:
    """Validate the connection by hitting the health endpoint."""
    client = CamspeakApiClient(
        url,
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
            url = _parse_url(user_input[CONF_URL])
            verify_ssl = user_input[CONF_VERIFY_SSL]
            if await _test_connection(self.hass, url, verify_ssl):
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"camspeak ({url})",
                    data={CONF_URL: url, CONF_VERIFY_SSL: verify_ssl},
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

        # Try http first, then https
        for scheme in ("http", "https"):
            url = f"{scheme}://{host}:{port}"
            for verify_ssl in (False, True):
                if scheme == "http" and verify_ssl:
                    continue
                if await _test_connection(self.hass, url, verify_ssl):
                    await self.async_set_unique_id(url)
                    self._abort_if_unique_id_configured()
                    self._discovery_data = {
                        CONF_URL: url,
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
                title=f"camspeak ({self._discovery_data[CONF_URL]})",
                data=self._discovery_data,
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._discovery_data[CONF_URL]},
        )
