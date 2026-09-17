"""Tests for the Karlsruhe SensorCity coordinator."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientError
from custom_components.karlsruhe_sensorcity.api import WeatherData
from custom_components.karlsruhe_sensorcity.coordinator import (
    KarlsruheSensorCityCoordinator,
)
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed


def create_weather_data() -> WeatherData:
    """Create test weather data."""
    return WeatherData(
        device_id="test-device",
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
        "test-device",
    )


@pytest.mark.asyncio
async def test_update_data(hass: HomeAssistant) -> None:
    """Test a successful coordinator update."""
    coordinator = create_coordinator(hass)

    data = create_weather_data()
    coordinator.api.get_latest = AsyncMock(return_value=data)

    result = await coordinator._async_update_data()

    assert result is data
    coordinator.api.get_latest.assert_awaited_once_with("test-device")


@pytest.mark.asyncio
async def test_update_data_value_error(hass: HomeAssistant) -> None:
    """Test handling a ValueError."""
    coordinator = create_coordinator(hass)

    coordinator.api.get_latest = AsyncMock(
        side_effect=ValueError("Invalid API response")
    )

    with pytest.raises(UpdateFailed, match="Invalid API response"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_client_error(hass: HomeAssistant) -> None:
    """Test handling an aiohttp ClientError."""
    coordinator = create_coordinator(hass)

    coordinator.api.get_latest = AsyncMock(side_effect=ClientError("Connection failed"))

    with pytest.raises(UpdateFailed, match="Connection failed"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_key_error(hass: HomeAssistant) -> None:
    """Test handling a KeyError."""
    coordinator = create_coordinator(hass)

    coordinator.api.get_latest = AsyncMock(side_effect=KeyError("temperature"))

    with pytest.raises(UpdateFailed, match="temperature"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_update_data_index_error(hass: HomeAssistant) -> None:
    """Test handling an IndexError."""
    coordinator = create_coordinator(hass)

    coordinator.api.get_latest = AsyncMock(side_effect=IndexError("No measurement"))

    with pytest.raises(UpdateFailed, match="No measurement"):
        await coordinator._async_update_data()
