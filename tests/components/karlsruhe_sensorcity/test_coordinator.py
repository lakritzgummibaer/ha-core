"""Tests for the Karlsruhe SensorCity coordinator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientError
from custom_components.karlsruhe_sensorcity.api import WeatherData
from custom_components.karlsruhe_sensorcity.const import SensorType
from custom_components.karlsruhe_sensorcity.coordinator import (
    KarlsruheSensorCityCoordinator,
)
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

DEVICE_ID = "test-device"


def create_sensor_data() -> WeatherData:
    """Create test sensor data."""
    return WeatherData(
        device_id=DEVICE_ID,
        name="Teststation",
        measured_at=datetime(2026, 9, 17, 10, 0, tzinfo=UTC),
        latitude=49.009,
        longitude=8.404,
        temperature=21.5,
        humidity=62.0,
        pressure=100090,
        solar_radiation=434.0,
    )


def create_coordinator(
    hass: HomeAssistant,
) -> KarlsruheSensorCityCoordinator:
    """Create a coordinator with a mocked session."""
    session = MagicMock()

    return KarlsruheSensorCityCoordinator(
        hass,
        session,
        sensor_type=SensorType.WEATHER,
        device_ids=[DEVICE_ID],
    )


@pytest.mark.asyncio
async def test_update_data(hass: HomeAssistant) -> None:
    """Test a successful coordinator update."""
    coordinator = create_coordinator(hass)
    data = create_sensor_data()

    coordinator.api.get_latest = AsyncMock(return_value=data)

    result = await coordinator._async_update_data()

    assert result == {DEVICE_ID: data}
    coordinator.api.get_latest.assert_awaited_once_with(
        DEVICE_ID,
        SensorType.WEATHER,
    )


@pytest.mark.parametrize(
    "error",
    [
        ValueError("Invalid API response"),
        ClientError("Connection failed"),
        KeyError("temperature"),
        IndexError("No measurement"),
        TimeoutError("Request timed out"),
    ],
)
@pytest.mark.asyncio
async def test_update_data_error(
    hass: HomeAssistant,
    error: Exception,
) -> None:
    """Test handling API errors."""
    coordinator = create_coordinator(hass)
    coordinator.api.get_latest = AsyncMock(side_effect=error)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_failed_refresh_notifies_listeners(
    hass: HomeAssistant,
) -> None:
    """Test that a failed refresh notifies coordinator listeners."""
    coordinator = create_coordinator(hass)
    coordinator.api.get_latest = AsyncMock(side_effect=ClientError("Connection failed"))

    listener = MagicMock()
    coordinator.async_add_listener(listener)

    await coordinator.async_refresh()

    listener.assert_called_once()
    assert coordinator.last_update_success is False
