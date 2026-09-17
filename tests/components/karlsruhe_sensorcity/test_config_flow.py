"""Tests for the Karlsruhe SensorCity config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
from custom_components.karlsruhe_sensorcity.config_flow import (
    KarlsruheSensorCityConfigFlow,
)
from custom_components.karlsruhe_sensorcity.const import CONF_DEVICE_ID

from homeassistant.core import HomeAssistant


async def test_station_list_is_provided(
    hass: HomeAssistant,
) -> None:
    """Test that stations are provided by the API client."""
    stations = {
        "device-2": "Station B",
        "device-1": "Station A",
    }

    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".KarlsruheSensorCityApi.get_stations",
            new=AsyncMock(return_value=stations),
        ),
    ):
        result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert CONF_DEVICE_ID in result["data_schema"].schema

    selector = result["data_schema"].schema[CONF_DEVICE_ID]
    options = selector.config["options"]

    assert options == [
        {"value": "device-1", "label": "Station A"},
        {"value": "device-2", "label": "Station B"},
    ]


async def test_api_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test handling of a connection error."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".KarlsruheSensorCityApi.get_stations",
            new=AsyncMock(side_effect=ClientError("Connection failed")),
        ),
    ):
        result = await flow.async_step_user()

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_api_value_error(
    hass: HomeAssistant,
) -> None:
    """Test handling of an invalid API response."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.karlsruhe_sensorcity.config_flow"
            ".KarlsruheSensorCityApi.get_stations",
            new=AsyncMock(side_effect=ValueError("Invalid API response")),
        ),
    ):
        result = await flow.async_step_user()

    assert result["type"] == "abort"
    assert result["reason"] == "invalid_request"
