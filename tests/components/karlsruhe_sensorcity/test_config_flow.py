"""Tests for the Karlsruhe SensorCity config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
from custom_components.karlsruhe_sensorcity.api import Station
from custom_components.karlsruhe_sensorcity.config_flow import (
    KarlsruheSensorCityConfigFlow,
)
from custom_components.karlsruhe_sensorcity.const import (
    CONF_DEVICE_IDS,
    CONF_SENSOR_TYPE,
    SensorType,
)
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow

API_PATH = (
    "custom_components.karlsruhe_sensorcity.config_flow."
    "KarlsruheSensorCityApi.get_stations"
)
SESSION_PATH = (
    "custom_components.karlsruhe_sensorcity.config_flow.async_get_clientsession"
)


async def test_user_step_shows_sensor_type_selector(
    hass: HomeAssistant,
) -> None:
    """Test that the first step asks for a sensor type."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert CONF_SENSOR_TYPE in result["data_schema"].schema


async def test_user_step_aborts_if_sensor_type_is_configured(
    hass: HomeAssistant,
) -> None:
    """Test that an existing entry is detected in the first step."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass

    with (
        patch.object(flow, "async_set_unique_id", new=AsyncMock()),
        patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=AbortFlow("already_configured"),
        ) as abort_check,
        pytest.raises(AbortFlow, match="already_configured"),
    ):
        await flow.async_step_user({CONF_SENSOR_TYPE: SensorType.WEATHER.value})

    abort_check.assert_called_once()


async def test_station_list_is_provided(
    hass: HomeAssistant,
) -> None:
    """Test that stations are provided by the API client and sorted."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    stations = [
        Station(device_id="device-2", name="Station B"),
        Station(device_id="device-1", name="Station A"),
    ]

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(API_PATH, new=AsyncMock(return_value=stations)),
    ):
        result = await flow.async_step_stations()

    assert result["type"] == "form"
    assert result["step_id"] == "stations"
    assert CONF_DEVICE_IDS in result["data_schema"].schema

    station_selector = result["data_schema"].schema[CONF_DEVICE_IDS]

    assert station_selector.options == {
        "device-1": "Station A",
        "device-2": "Station B",
    }


async def test_api_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test handling of a connection error while loading stations."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(
            API_PATH,
            new=AsyncMock(side_effect=ClientError("Connection failed")),
        ),
    ):
        result = await flow.async_step_stations()

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_api_value_error(
    hass: HomeAssistant,
) -> None:
    """Test handling of an invalid API response."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(
            API_PATH,
            new=AsyncMock(side_effect=ValueError("Invalid API response")),
        ),
    ):
        result = await flow.async_step_stations()

    assert result["type"] == "abort"
    assert result["reason"] == "invalid_request"


async def test_no_stations_found(
    hass: HomeAssistant,
) -> None:
    """Test handling when the API returns no stations."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(API_PATH, new=AsyncMock(return_value=[])),
    ):
        result = await flow.async_step_stations()

    assert result["type"] == "abort"
    assert result["reason"] == "no_stations"


async def test_empty_station_selection_shows_error(
    hass: HomeAssistant,
) -> None:
    """Test that an empty station selection is rejected."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    stations = [Station(device_id="device-1", name="Station A")]

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(API_PATH, new=AsyncMock(return_value=stations)),
    ):
        result = await flow.async_step_stations({CONF_DEVICE_IDS: []})

        assert result["type"] == "form"
        assert result["step_id"] == "stations"
        assert result["errors"] == {CONF_DEVICE_IDS: "no_stations_selected"}

        result = await flow.async_step_stations({CONF_DEVICE_IDS: ["device-1"]})

    assert result["type"] == "create_entry"
    assert result["data"][CONF_SENSOR_TYPE] == SensorType.WEATHER
    assert result["data"][CONF_DEVICE_IDS] == ["device-1"]


async def test_multiple_stations_create_entry(
    hass: HomeAssistant,
) -> None:
    """Test creating an entry with multiple selected stations."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WEATHER

    selected_ids = ["device-1", "device-2"]

    result = await flow.async_step_stations({CONF_DEVICE_IDS: selected_ids})

    assert result["type"] == "create_entry"
    assert result["data"][CONF_SENSOR_TYPE] == SensorType.WEATHER
    assert result["data"][CONF_DEVICE_IDS] == selected_ids
    assert result["title"] == "SensorCity - Weather"


async def test_wind_sensor_type_is_passed_to_api(
    hass: HomeAssistant,
) -> None:
    """Test that the selected sensor type is passed to the API."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WIND

    stations = [
        Station(device_id="wind-1", name="Windstation A"),
    ]

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(
            API_PATH,
            new=AsyncMock(return_value=stations),
        ) as get_stations,
    ):
        result = await flow.async_step_stations()

    assert result["type"] == "form"
    get_stations.assert_awaited_once_with(SensorType.WIND)


async def test_wind_stations_create_entry(
    hass: HomeAssistant,
) -> None:
    """Test creating an entry for wind sensors."""
    flow = KarlsruheSensorCityConfigFlow()
    flow.hass = hass
    flow.sensor_type = SensorType.WIND

    selected_ids = ["wind-1", "wind-2"]

    result = await flow.async_step_stations({CONF_DEVICE_IDS: selected_ids})

    assert result["type"] == "create_entry"
    assert result["data"][CONF_SENSOR_TYPE] == SensorType.WIND
    assert result["data"][CONF_DEVICE_IDS] == selected_ids
    assert result["title"] == "SensorCity - Wind"
