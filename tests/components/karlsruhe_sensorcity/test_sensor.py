"""Tests for the Karlsruhe SensorCity sensors."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from custom_components.karlsruhe_sensorcity.api import WeatherData
from custom_components.karlsruhe_sensorcity.const import MAX_DATA_AGE
from custom_components.karlsruhe_sensorcity.sensor import (
    SENSORS,
    KarlsruheSensorCitySensor,
)
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util


def create_weather_data(
    *,
    measured_at: datetime | None = None,
    temperature: float | None = 21.5,
    humidity: float | None = 62.0,
    pressure: float | None = 100090,
    solar_radiation: float | None = 434.0,
    latitude: float | None = 49.009,
    longitude: float | None = 8.404,
) -> WeatherData:
    """Create test weather data."""
    return WeatherData(
        device_id="test-device",
        name="Teststation",
        measured_at=measured_at or dt_util.utcnow(),
        latitude=latitude,
        longitude=longitude,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        solar_radiation=solar_radiation,
    )


def create_coordinator(data: WeatherData | None) -> MagicMock:
    """Create a mocked coordinator."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.device_id = "test-device"
    return coordinator


def create_entry() -> MagicMock:
    """Create a mocked config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test-entry"
    return entry


def test_sensor_descriptions() -> None:
    """Test that all expected sensors are defined."""
    assert len(SENSORS) == 4

    assert {description.key for description in SENSORS} == {
        "temperature",
        "humidity",
        "pressure",
        "solar_radiation",
    }


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("temperature", 21.5),
        ("humidity", 62.0),
        ("pressure", 1000.9),
        ("solar_radiation", 434.0),
    ],
)
def test_sensor_value(key: str, expected: float) -> None:
    """Test sensor values."""
    data = create_weather_data()
    coordinator = create_coordinator(data)
    entry = create_entry()

    description = next(description for description in SENSORS if description.key == key)

    sensor = KarlsruheSensorCitySensor(
        coordinator,
        entry,
        description,
    )

    assert sensor.native_value == expected


@pytest.mark.parametrize(
    ("key", "unit", "device_class"),
    [
        (
            "temperature",
            "°C",
            "temperature",
        ),
        (
            "humidity",
            "%",
            "humidity",
        ),
        (
            "pressure",
            "hPa",
            "atmospheric_pressure",
        ),
        (
            "solar_radiation",
            "W/m²",
            None,
        ),
    ],
)
def test_sensor_units(
    key: str,
    unit: str,
    device_class: str | None,
) -> None:
    """Test sensor units and device classes."""
    description = next(description for description in SENSORS if description.key == key)

    assert description.native_unit_of_measurement == unit

    if device_class is None:
        assert description.device_class is None
    else:
        assert description.device_class.value == device_class


@pytest.mark.parametrize(
    "key",
    [
        "temperature",
        "humidity",
        "pressure",
        "solar_radiation",
    ],
)
def test_sensor_missing_value(key: str) -> None:
    """Test sensors with missing measurement values."""
    data = create_weather_data(
        temperature=None if key == "temperature" else 21.5,
        humidity=None if key == "humidity" else 62.0,
        pressure=None if key == "pressure" else 100090,
        solar_radiation=None if key == "solar_radiation" else 434.0,
    )
    coordinator = create_coordinator(data)
    entry = create_entry()

    description = next(description for description in SENSORS if description.key == key)

    sensor = KarlsruheSensorCitySensor(
        coordinator,
        entry,
        description,
    )

    assert sensor.native_value is None


def test_sensor_available_with_fresh_data() -> None:
    """Test that a fresh measurement is available."""
    data = create_weather_data(
        measured_at=dt_util.utcnow() - timedelta(minutes=1),
    )
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    assert sensor.available is True


def test_sensor_unavailable_with_stale_data() -> None:
    """Test that a stale measurement is unavailable."""
    data = create_weather_data(
        measured_at=dt_util.utcnow() - MAX_DATA_AGE - timedelta(minutes=1),
    )
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    assert sensor.available is False


def test_sensor_unavailable_without_data() -> None:
    """Test that a sensor is unavailable without coordinator data."""
    data = create_weather_data()
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    coordinator.data = None

    assert sensor.available is False


def test_sensor_station_attributes() -> None:
    """Test station information attributes."""
    measured_at = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
    data = create_weather_data(measured_at=measured_at)
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    assert sensor.extra_state_attributes == {
        "last_measurement": measured_at.isoformat(),
        "latitude": 49.009,
        "longitude": 8.404,
    }


def test_sensor_missing_coordinates() -> None:
    """Test station information with missing coordinates."""
    data = create_weather_data(
        latitude=None,
        longitude=None,
    )
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    assert sensor.extra_state_attributes["latitude"] is None
    assert sensor.extra_state_attributes["longitude"] is None


def test_sensor_station_attributes_without_data() -> None:
    """Test station information without coordinator data."""
    data = create_weather_data()
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(coordinator, create_entry(), SENSORS[0])

    coordinator.data = None

    assert sensor.extra_state_attributes == {}
