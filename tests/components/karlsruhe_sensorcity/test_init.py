"""Tests for the Karlsruhe SensorCity integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.karlsruhe_sensorcity import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.karlsruhe_sensorcity.const import (
    CONF_DEVICE_IDS,
    CONF_SENSOR_TYPE,
    DOMAIN,
    SensorType,
)

from homeassistant.core import HomeAssistant

SESSION_PATH = "custom_components.karlsruhe_sensorcity.async_get_clientsession"
COORDINATOR_PATH = (
    "custom_components.karlsruhe_sensorcity.KarlsruheSensorCityCoordinator"
)


async def test_setup_entry(
    hass: HomeAssistant,
) -> None:
    """Test setting up the integration."""
    device_ids = ["device-1", "device-2"]
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.data = {
        CONF_SENSOR_TYPE: SensorType.WEATHER.value,
        CONF_DEVICE_IDS: device_ids,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(COORDINATOR_PATH, return_value=coordinator) as coordinator_class,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ) as forward_setups,
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True

    coordinator_class.assert_called_once_with(
        hass,
        coordinator_class.call_args.args[1],
        sensor_type=SensorType.WEATHER,
        device_ids=device_ids,
    )
    coordinator.async_config_entry_first_refresh.assert_awaited_once_with()
    forward_setups.assert_awaited_once_with(entry, ["sensor"])
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    entry.async_on_unload.assert_called_once()


async def test_setup_entry_uses_station_options(
    hass: HomeAssistant,
) -> None:
    """Test that configured station options override the original selection."""
    entry = MagicMock()
    entry.entry_id = "test-entry-options"
    entry.data = {
        CONF_SENSOR_TYPE: SensorType.WIND.value,
        CONF_DEVICE_IDS: ["wind-1"],
    }
    entry.options = {
        CONF_DEVICE_IDS: ["wind-2", "wind-3"],
    }
    entry.async_on_unload = MagicMock()

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    with (
        patch(SESSION_PATH, return_value=MagicMock()),
        patch(COORDINATOR_PATH, return_value=coordinator) as coordinator_class,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        await async_setup_entry(hass, entry)

    assert coordinator_class.call_args.kwargs["sensor_type"] is SensorType.WIND
    assert coordinator_class.call_args.kwargs["device_ids"] == [
        "wind-2",
        "wind-3",
    ]


async def test_unload_entry_success(
    hass: HomeAssistant,
) -> None:
    """Test unloading the integration successfully."""
    entry = MagicMock()
    entry.entry_id = "test-entry"

    coordinator = MagicMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=True),
    ) as unload_platforms:
        result = await async_unload_entry(hass, entry)

    assert result is True
    unload_platforms.assert_awaited_once_with(entry, ["sensor"])
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_unload_entry_failure(
    hass: HomeAssistant,
) -> None:
    """Test retaining the coordinator when unloading fails."""
    entry = MagicMock()
    entry.entry_id = "test-entry"

    coordinator = MagicMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=False),
    ) as unload_platforms:
        result = await async_unload_entry(hass, entry)

    assert result is False
    unload_platforms.assert_awaited_once_with(entry, ["sensor"])
    assert hass.data[DOMAIN][entry.entry_id] is coordinator


async def test_reload_entry_removes_deselected_station(
    hass: HomeAssistant,
) -> None:
    """Test removing entities and device for a deselected station."""
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.data = {
        CONF_SENSOR_TYPE: SensorType.WEATHER.value,
        CONF_DEVICE_IDS: ["device-1", "device-2"],
    }
    entry.options = {
        CONF_DEVICE_IDS: ["device-2"],
    }

    coordinator = MagicMock()
    coordinator.device_ids = ["device-1", "device-2"]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entity = MagicMock()
    entity.config_entry_id = entry.entry_id
    entity.unique_id = "device-1_temperature"
    entity.entity_id = "sensor.device_1_temperature"
    entity.device_id = "registered-device-1"

    entity_registry = MagicMock()
    entity_registry.entities = {entity.entity_id: entity}
    entity_registry.async_remove.side_effect = entity_registry.entities.pop

    device = MagicMock()
    device.id = "registered-device-1"

    device_registry = MagicMock()
    device_registry.async_get_device_by_identifier.return_value = device

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.entity_registry.async_get",
            return_value=entity_registry,
        ),
        patch(
            "custom_components.karlsruhe_sensorcity.device_registry.async_get",
            return_value=device_registry,
        ),
        patch.object(
            hass.config_entries,
            "async_reload",
            new=AsyncMock(),
        ) as reload_entry,
    ):
        await async_reload_entry(hass, entry)

    entity_registry.async_remove.assert_called_once_with("sensor.device_1_temperature")
    device_registry.async_remove_device.assert_called_once_with("registered-device-1")
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_reload_entry_keeps_device_with_remaining_entities(
    hass: HomeAssistant,
) -> None:
    """Test keeping a device that still has registered entities."""
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.data = {
        CONF_SENSOR_TYPE: SensorType.WEATHER.value,
        CONF_DEVICE_IDS: ["device-1", "device-2"],
    }
    entry.options = {
        CONF_DEVICE_IDS: ["device-2"],
    }

    coordinator = MagicMock()
    coordinator.device_ids = ["device-1", "device-2"]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    removed_entity = MagicMock()
    removed_entity.config_entry_id = entry.entry_id
    removed_entity.unique_id = "device-1_temperature"
    removed_entity.entity_id = "sensor.device_1_temperature"
    removed_entity.device_id = "registered-device-1"

    remaining_entity = MagicMock()
    remaining_entity.config_entry_id = entry.entry_id
    remaining_entity.unique_id = "device-2_temperature"
    remaining_entity.entity_id = "sensor.device_2_temperature"
    remaining_entity.device_id = "registered-device-1"

    entity_registry = MagicMock()
    entity_registry.entities = {
        removed_entity.entity_id: removed_entity,
        remaining_entity.entity_id: remaining_entity,
    }
    entity_registry.async_remove.side_effect = entity_registry.entities.pop

    device = MagicMock()
    device.id = "registered-device-1"

    device_registry = MagicMock()
    device_registry.async_get_device_by_identifier.return_value = device

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.entity_registry.async_get",
            return_value=entity_registry,
        ),
        patch(
            "custom_components.karlsruhe_sensorcity.device_registry.async_get",
            return_value=device_registry,
        ),
        patch.object(
            hass.config_entries,
            "async_reload",
            new=AsyncMock(),
        ) as reload_entry,
    ):
        await async_reload_entry(hass, entry)

    entity_registry.async_remove.assert_called_once_with(removed_entity.entity_id)
    device_registry.async_remove_device.assert_not_called()
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_reload_entry_without_coordinator(
    hass: HomeAssistant,
) -> None:
    """Test reloading when no coordinator is stored."""
    entry = MagicMock()
    entry.entry_id = "missing-coordinator-entry"

    entity_registry = MagicMock()
    device_registry = MagicMock()

    with (
        patch(
            "custom_components.karlsruhe_sensorcity.entity_registry.async_get",
            return_value=entity_registry,
        ) as get_entity_registry,
        patch(
            "custom_components.karlsruhe_sensorcity.device_registry.async_get",
            return_value=device_registry,
        ) as get_device_registry,
        patch.object(
            hass.config_entries,
            "async_reload",
            new=AsyncMock(),
        ) as reload_entry,
    ):
        await async_reload_entry(hass, entry)

    get_entity_registry.assert_not_called()
    get_device_registry.assert_not_called()
    reload_entry.assert_awaited_once_with(entry.entry_id)
