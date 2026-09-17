"""Tests for the Karlsruhe SensorCity API client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from custom_components.karlsruhe_sensorcity.api import KarlsruheSensorCityApi
from custom_components.karlsruhe_sensorcity.const import (
    API_URL,
    CURRENT_LAYER,
    REQUEST_TIMEOUT,
)
import pytest


def create_response(data: dict) -> MagicMock:
    """Create a mock HTTP response."""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=data)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


@pytest.mark.asyncio
async def test_get_latest() -> None:
    """Test retrieving the latest measurement."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "test-device",
                        "name": "Teststation",
                        "measured_at": 1750000000000,
                        "temp": 21.5,
                        "luftfeuchte": 62.0,
                        "press": 100090,
                        "sonnenstrahlung": 434.0,
                    },
                    "geometry": {
                        "x": 8.404,
                        "y": 49.009,
                    },
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    result = await api.get_latest("test-device")

    assert result.device_id == "test-device"
    assert result.name == "Teststation"
    assert result.measured_at == datetime.fromtimestamp(
        1750000000000 / 1000,
        tz=UTC,
    )
    assert result.temperature == 21.5
    assert result.humidity == 62.0
    assert result.pressure == 100090
    assert result.solar_radiation == 434.0
    assert result.latitude == 49.009
    assert result.longitude == 8.404

    session.get.assert_called_once_with(
        f"{API_URL}/{CURRENT_LAYER}",
        params={
            "where": "device_id = 'test-device'",
            "outFields": (
                "device_id,name,measured_at,temp,luftfeuchte,press,sonnenstrahlung"
            ),
            "orderByFields": "measured_at DESC",
            "resultRecordCount": 1,
            "returnGeometry": "true",
            "f": "json",
        },
        timeout=REQUEST_TIMEOUT,
    )


@pytest.mark.asyncio
async def test_get_latest_without_geometry() -> None:
    """Test retrieving a measurement without geometry."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "test-device",
                        "name": "Teststation",
                        "measured_at": 1750000000000,
                        "temp": 21.5,
                        "luftfeuchte": 62.0,
                        "press": 100090,
                        "sonnenstrahlung": 434.0,
                    },
                    "geometry": None,
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    result = await api.get_latest("test-device")

    assert result.latitude is None
    assert result.longitude is None


@pytest.mark.asyncio
async def test_get_latest_with_missing_measurement() -> None:
    """Test retrieving a measurement with missing values."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "test-device",
                        "name": "Teststation",
                        "measured_at": 1750000000000,
                        "temp": 21.5,
                        "luftfeuchte": None,
                        "press": 100090,
                        "sonnenstrahlung": None,
                    },
                    "geometry": {
                        "x": 8.404,
                        "y": 49.009,
                    },
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    result = await api.get_latest("test-device")

    assert result.temperature == 21.5
    assert result.humidity is None
    assert result.pressure == 100090
    assert result.solar_radiation is None


@pytest.mark.asyncio
async def test_get_latest_without_features() -> None:
    """Test handling an empty API response."""
    response = create_response({"features": []})

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="No measurements found"):
        await api.get_latest("test-device")


@pytest.mark.asyncio
async def test_get_latest_with_api_error() -> None:
    """Test handling an API error response."""
    response = create_response(
        {
            "error": {
                "message": "Invalid query",
            }
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="Invalid query"):
        await api.get_latest("test-device")


@pytest.mark.asyncio
async def test_get_stations() -> None:
    """Test retrieving available stations."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "station-1",
                        "name": "Station Eins",
                    }
                },
                {
                    "attributes": {
                        "device_id": "station-2",
                        "name": "Station Zwei",
                    }
                },
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    result = await api.get_stations()

    assert result == {
        "station-1": "Station Eins",
        "station-2": "Station Zwei",
    }

    session.get.assert_called_once_with(
        f"{API_URL}/{CURRENT_LAYER}",
        params={
            "where": "beschreibung = 'Temperatur-Sensor'",
            "outFields": "device_id,name",
            "returnDistinctValues": "true",
            "returnGeometry": "true",
            "f": "json",
        },
    )


@pytest.mark.asyncio
async def test_get_stations_removes_duplicates() -> None:
    """Test that duplicate device IDs are removed."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "station-1",
                        "name": "Alter Name",
                    }
                },
                {
                    "attributes": {
                        "device_id": "station-1",
                        "name": "Aktueller Name",
                    }
                },
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    result = await api.get_stations()

    assert result == {"station-1": "Aktueller Name"}


@pytest.mark.asyncio
async def test_get_stations_without_features() -> None:
    """Test handling an empty station response."""
    response = create_response({"features": []})

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="No stations found"):
        await api.get_stations()


@pytest.mark.asyncio
async def test_get_stations_without_attributes() -> None:
    """Test handling a station without attributes."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": None,
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="Missing attributes"):
        await api.get_stations()


@pytest.mark.asyncio
async def test_get_stations_with_api_error() -> None:
    """Test handling an API error response."""
    response = create_response(
        {
            "error": {
                "message": "Invalid query",
            }
        }
    )

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="Invalid query"):
        await api.get_stations()
