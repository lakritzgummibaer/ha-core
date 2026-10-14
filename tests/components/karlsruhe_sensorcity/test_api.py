"""Tests for the Karlsruhe SensorCity API client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from custom_components.karlsruhe_sensorcity.api import KarlsruheSensorCityApi, Station
from custom_components.karlsruhe_sensorcity.const import (
    API_URL,
    CURRENT_LAYER,
    REQUEST_TIMEOUT,
    SensorType,
)
import pytest

DEVICE_ID = "test-device"


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

    result = await api.get_latest(DEVICE_ID, SensorType.WEATHER)

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
async def test_get_latest_wind() -> None:
    """Test retrieving the latest wind measurement."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": DEVICE_ID,
                        "name": "Windstation",
                        "measured_at": 1750000000000,
                        "wind_average_kmh": 12.4,
                        "windgust_1s_kmh": 28.7,
                        "windgust_3s_kmh": 24.2,
                        "wind_direction_degree": 225,
                    },
                    "geometry": {"x": 8.404, "y": 49.009},
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response
    api = KarlsruheSensorCityApi(session)

    result = await api.get_latest(DEVICE_ID, SensorType.WIND)

    assert result.device_id == DEVICE_ID
    assert result.name == "Windstation"
    assert result.measured_at == datetime.fromtimestamp(
        1750000000000 / 1000,
        tz=UTC,
    )
    assert result.wind_average_speed == 12.4
    assert result.wind_gust_1s == 28.7
    assert result.wind_gust_3s == 24.2
    assert result.wind_direction == 225
    assert result.latitude == 49.009
    assert result.longitude == 8.404

    session.get.assert_called_once_with(
        f"{API_URL}/{CURRENT_LAYER}",
        params={
            "where": f"device_id = '{DEVICE_ID}'",
            "outFields": (
                "device_id,name,measured_at,wind_average_kmh,"
                "windgust_1s_kmh,windgust_3s_kmh,wind_direction_degree"
            ),
            "orderByFields": "measured_at DESC",
            "resultRecordCount": 1,
            "returnGeometry": "true",
            "f": "json",
        },
        timeout=REQUEST_TIMEOUT,
    )


@pytest.mark.asyncio
async def test_get_latest_wind_with_missing_measurements() -> None:
    """Test retrieving wind measurements with missing values."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": DEVICE_ID,
                        "name": "Windstation",
                        "measured_at": 1750000000000,
                        "wind_average_kmh": None,
                        "windgust_1s_kmh": None,
                        "windgust_3s_kmh": 8.5,
                        "wind_direction_degree": None,
                    },
                    "geometry": None,
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response
    api = KarlsruheSensorCityApi(session)

    result = await api.get_latest(DEVICE_ID, SensorType.WIND)

    assert result.wind_average_speed is None
    assert result.wind_gust_1s is None
    assert result.wind_gust_3s == 8.5
    assert result.wind_direction is None
    assert result.latitude is None
    assert result.longitude is None


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

    result = await api.get_latest(DEVICE_ID, SensorType.WEATHER)

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

    result = await api.get_latest(DEVICE_ID, SensorType.WEATHER)

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
        await api.get_latest(DEVICE_ID, SensorType.WEATHER)


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
        await api.get_latest(DEVICE_ID, SensorType.WEATHER)


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

    result = await api.get_stations(SensorType.WEATHER)

    assert result == [
        Station(device_id="station-1", name="Station Eins"),
        Station(device_id="station-2", name="Station Zwei"),
    ]

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
async def test_get_stations_wind() -> None:
    """Test retrieving available wind stations."""
    response = create_response(
        {
            "features": [
                {
                    "attributes": {
                        "device_id": "wind-station-1",
                        "name": "Windstation Eins",
                    }
                }
            ]
        }
    )

    session = MagicMock()
    session.get.return_value = response
    api = KarlsruheSensorCityApi(session)

    result = await api.get_stations(SensorType.WIND)

    assert result == [
        Station(
            device_id="wind-station-1",
            name="Windstation Eins",
        ),
    ]

    session.get.assert_called_once_with(
        f"{API_URL}/{CURRENT_LAYER}",
        params={
            "where": "beschreibung = 'Wind-Sensor'",
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

    result = await api.get_stations(SensorType.WEATHER)

    assert result == [
        Station(device_id="station-1", name="Aktueller Name"),
    ]


@pytest.mark.asyncio
async def test_get_stations_without_features() -> None:
    """Test handling an empty station response."""
    response = create_response({"features": []})

    session = MagicMock()
    session.get.return_value = response

    api = KarlsruheSensorCityApi(session)

    with pytest.raises(ValueError, match="No stations found"):
        await api.get_stations(SensorType.WEATHER)


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
        await api.get_stations(SensorType.WEATHER)


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
        await api.get_stations(SensorType.WEATHER)
