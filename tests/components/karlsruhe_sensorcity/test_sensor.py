"""Tests for the Karlsruhe SensorCity sensors."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from custom_components.karlsruhe_sensorcity.api import WeatherData, WindData
from custom_components.karlsruhe_sensorcity.const import (
    DOMAIN,
    MAX_DATA_AGE,
    WIND_DIRECTION_MIN_SPEED,
    SensorType,
)
from custom_components.karlsruhe_sensorcity.sensor import (
    WEATHER_SENSORS,
    WIND_SENSORS,
    KarlsruheSensorCitySensor,
    async_setup_entry,
)
import pytest

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

DEVICE_ID = "test-device"


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


def create_wind_data(
    *,
    measured_at: datetime | None = None,
    wind_average_speed: float | None = 12.4,
    wind_gust_1s: float | None = 28.7,
    wind_gust_3s: float | None = 24.2,
    wind_direction: int | None = 225,
    latitude: float | None = 49.009,
    longitude: float | None = 8.404,
) -> WindData:
    """Create test wind data."""
    return WindData(
        device_id=DEVICE_ID,
        name="Teststation",
        measured_at=measured_at or dt_util.utcnow(),
        latitude=latitude,
        longitude=longitude,
        wind_average_speed=wind_average_speed,
        wind_gust_1s=wind_gust_1s,
        wind_gust_3s=wind_gust_3s,
        wind_direction=wind_direction,
    )


def create_coordinator(
    data: WeatherData | WindData | None,
    sensor_type: SensorType = SensorType.WEATHER,
) -> MagicMock:
    """Create a mocked coordinator."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.sensor_type = sensor_type
    coordinator.device_ids = [DEVICE_ID]
    coordinator.data = {DEVICE_ID: data} if data is not None else {}
    return coordinator


def test_sensor_descriptions() -> None:
    """Test that all expected sensors are defined."""
    assert len(WEATHER_SENSORS) == 4

    assert {description.key for description in WEATHER_SENSORS} == {
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

    description = next(
        description for description in WEATHER_SENSORS if description.key == key
    )

    sensor = KarlsruheSensorCitySensor(
        coordinator,
        description,
        DEVICE_ID,
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
    description = next(
        description for description in WEATHER_SENSORS if description.key == key
    )

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

    description = next(
        description for description in WEATHER_SENSORS if description.key == key
    )

    sensor = KarlsruheSensorCitySensor(
        coordinator,
        description,
        DEVICE_ID,
    )

    assert sensor.native_value is None


def test_sensor_available_with_fresh_data() -> None:
    """Test that a fresh measurement is available."""
    data = create_weather_data(
        measured_at=dt_util.utcnow() - timedelta(minutes=1),
    )
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    assert sensor.available is True


def test_sensor_unavailable_with_stale_data() -> None:
    """Test that a stale measurement is unavailable."""
    data = create_weather_data(
        measured_at=dt_util.utcnow() - MAX_DATA_AGE - timedelta(minutes=1),
    )
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    assert sensor.available is False


def test_sensor_unavailable_without_data() -> None:
    """Test that a sensor is unavailable without coordinator data."""
    data = create_weather_data()
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    coordinator.data = {}

    assert sensor.available is False


def test_sensor_station_attributes() -> None:
    """Test station information attributes."""
    measured_at = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
    data = create_weather_data(measured_at=measured_at)
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

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
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    assert sensor.extra_state_attributes["latitude"] is None
    assert sensor.extra_state_attributes["longitude"] is None


def test_sensor_station_attributes_without_data() -> None:
    """Test station information without coordinator data."""
    data = create_weather_data()
    coordinator = create_coordinator(data)
    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    coordinator.data = {}

    assert sensor.extra_state_attributes == {}


def test_sensor_unavailable_after_25_minutes_without_update() -> None:
    """Test that a sensor becomes unavailable when its data gets stale."""
    data = create_weather_data(
        measured_at=dt_util.utcnow() - MAX_DATA_AGE - timedelta(seconds=1),
    )
    coordinator = create_coordinator(data)

    sensor = KarlsruheSensorCitySensor(
        coordinator,
        WEATHER_SENSORS[0],
        DEVICE_ID,
    )

    assert sensor.available is False


def test_wind_sensor_descriptions() -> None:
    """Test that all expected wind sensors are defined."""
    assert len(WIND_SENSORS) == 4

    assert {description.key for description in WIND_SENSORS} == {
        "wind_average_speed",
        "wind_gust_1s",
        "wind_gust_3s",
        "wind_direction",
    }


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("wind_average_speed", 12.4),
        ("wind_gust_1s", 28.7),
        ("wind_gust_3s", 24.2),
        ("wind_direction", 225),
    ],
)
def test_wind_sensor_value(key: str, expected: float) -> None:
    """Test wind sensor values."""
    data = create_wind_data()
    coordinator = create_coordinator(data, SensorType.WIND)

    description = next(
        description for description in WIND_SENSORS if description.key == key
    )

    sensor = KarlsruheSensorCitySensor(coordinator, description, DEVICE_ID)

    assert sensor.native_value == expected


@pytest.mark.parametrize(
    ("key", "unit", "device_class", "state_class"),
    [
        (
            "wind_average_speed",
            "km/h",
            "wind_speed",
            "measurement",
        ),
        (
            "wind_gust_1s",
            "km/h",
            "wind_speed",
            "measurement",
        ),
        (
            "wind_gust_3s",
            "km/h",
            "wind_speed",
            "measurement",
        ),
        (
            "wind_direction",
            "°",
            "wind_direction",
            "measurement_angle",
        ),
    ],
)
def test_wind_sensor_units_and_classes(
    key: str,
    unit: str,
    device_class: str,
    state_class: str,
) -> None:
    """Test wind sensor units and classes."""
    description = next(
        description for description in WIND_SENSORS if description.key == key
    )

    assert description.native_unit_of_measurement == unit
    assert description.device_class.value == device_class
    assert description.state_class.value == state_class


@pytest.mark.parametrize(
    "key",
    [
        "wind_average_speed",
        "wind_gust_1s",
        "wind_gust_3s",
        "wind_direction",
    ],
)
def test_wind_sensor_missing_value(key: str) -> None:
    """Test wind sensors with missing measurement values."""
    data = create_wind_data(
        wind_average_speed=None if key == "wind_average_speed" else 12.4,
        wind_gust_1s=None if key == "wind_gust_1s" else 28.7,
        wind_gust_3s=None if key == "wind_gust_3s" else 24.2,
        wind_direction=None if key == "wind_direction" else 225,
    )
    coordinator = create_coordinator(data, SensorType.WIND)

    description = next(
        description for description in WIND_SENSORS if description.key == key
    )

    sensor = KarlsruheSensorCitySensor(coordinator, description, DEVICE_ID)

    assert sensor.native_value is None


@pytest.mark.parametrize(
    ("sensor_type", "descriptions"),
    [
        (SensorType.WEATHER, WEATHER_SENSORS),
        (SensorType.WIND, WIND_SENSORS),
    ],
)
async def test_async_setup_entry(
    hass: HomeAssistant,
    sensor_type: SensorType,
    descriptions: tuple[SensorEntityDescription, ...],
) -> None:
    """Test that the correct sensors are created for a sensor type."""
    data = (
        create_weather_data()
        if sensor_type is SensorType.WEATHER
        else create_wind_data()
    )
    coordinator = create_coordinator(data, sensor_type)

    entry = MagicMock()
    entry.entry_id = "test-entry"

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    add_entities = MagicMock()

    await async_setup_entry(hass, entry, add_entities)

    add_entities.assert_called_once()
    entities = list(add_entities.call_args.args[0])

    assert len(entities) == len(descriptions)
    assert all(isinstance(entity, KarlsruheSensorCitySensor) for entity in entities)
    assert {entity.entity_description.key for entity in entities} == {
        description.key for description in descriptions
    }


def test_wind_direction_unavailable_at_low_speed() -> None:
    """Test that wind direction is omitted at low wind speeds."""
    data = create_wind_data(
        wind_average_speed=1.5,
        wind_direction=225,
    )
    coordinator = create_coordinator(data, SensorType.WIND)
    description = next(item for item in WIND_SENSORS if item.key == "wind_direction")

    sensor = KarlsruheSensorCitySensor(coordinator, description, DEVICE_ID)

    assert sensor.native_value is None


def test_wind_direction_unavailable_at_threshold_speed() -> None:
    """Test that wind direction is omitted at low wind speeds."""
    data = create_wind_data(
        wind_average_speed=WIND_DIRECTION_MIN_SPEED,
        wind_direction=225,
    )
    coordinator = create_coordinator(data, SensorType.WIND)
    description = next(item for item in WIND_SENSORS if item.key == "wind_direction")

    sensor = KarlsruheSensorCitySensor(coordinator, description, DEVICE_ID)

    assert sensor.native_value == 225
