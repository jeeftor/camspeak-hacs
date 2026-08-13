"""Tests for the camspeak config flow."""

from ipaddress import ip_address
from unittest.mock import AsyncMock

from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
import pytest

from custom_components.camspeak.const import CONF_VERIFY_SSL, DOMAIN

ZEROCONF_DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address("10.0.0.50"),
    ip_addresses=[ip_address("10.0.0.50")],
    hostname="camspeak.local.",
    name="camspeak._camspeak._tcp.local.",
    port=8585,
    type="_camspeak._tcp.local.",
    properties={
        "version": "1.0.0",
        "cameras": "2",
        "protocol": "https",
    },
)


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow(
    hass: HomeAssistant,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test full user setup flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "10.0.0.50",
            CONF_PORT: 8585,
            CONF_VERIFY_SSL: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "camspeak (10.0.0.50)"
    assert result["data"] == {
        CONF_HOST: "10.0.0.50",
        CONF_PORT: 8585,
        CONF_VERIFY_SSL: False,
    }


@pytest.mark.usefixtures("mock_setup_entry")
async def test_zeroconf_flow(
    hass: HomeAssistant,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test zeroconf discovery flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZEROCONF_DISCOVERY,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "camspeak (10.0.0.50)"
    assert result["data"][CONF_HOST] == "10.0.0.50"
    assert result["data"][CONF_PORT] == 8585  # noqa: PLR2004


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    mock_camspeak_client: AsyncMock,
) -> None:
    """Test user flow with connection error."""
    mock_camspeak_client.health.side_effect = Exception("connection refused")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "10.0.0.99",
            CONF_PORT: 8585,
            CONF_VERIFY_SSL: False,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
