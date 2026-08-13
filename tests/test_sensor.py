"""Tests for Google Health sensor platform."""

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from google_health_api.const import HealthApiScope
from google_health_api.model import (
    DailyHeartRateVariability,
    DailyOxygenSaturation,
    DailyRespiratoryRate,
    HeartRateVariability,
    OxygenSaturation,
    RespiratoryRateSleepSummary,
)
import pytest

from custom_components.google_health_plus.const import DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util.unit_system import (
    METRIC_SYSTEM,
    US_CUSTOMARY_SYSTEM,
    UnitSystem,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.usefixtures("mock_google_health_client")
async def test_all_entities(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test all sensor entities are registered with the expected device classes."""
    with patch("custom_components.google_health_plus._PLATFORMS", [Platform.SENSOR]):
        assert await integration_setup()

    expected = {
        # key -> (translation_key, device_class)
        "steps": ("steps", None),
        "distance": (None, SensorDeviceClass.DISTANCE),
        "active_calories": ("active_calories", SensorDeviceClass.ENERGY),
        "total_calories": ("total_calories", SensorDeviceClass.ENERGY),
        "floors": ("floors", None),
        "weight": (None, SensorDeviceClass.WEIGHT),
        "resting_heart_rate": ("resting_heart_rate", None),
        "body_fat": ("body_fat", None),
        "sleep_asleep": ("sleep_asleep", SensorDeviceClass.DURATION),
        "sleep_awake": ("sleep_awake", SensorDeviceClass.DURATION),
        "sleep_in_bed": ("sleep_in_bed", SensorDeviceClass.DURATION),
        "sleep_to_fall_asleep": ("sleep_to_fall_asleep", SensorDeviceClass.DURATION),
        "sleep_after_wakeup": ("sleep_after_wakeup", SensorDeviceClass.DURATION),
        "bedtime": ("bedtime", SensorDeviceClass.TIMESTAMP),
        "wake_time": ("wake_time", SensorDeviceClass.TIMESTAMP),
        "hydration": ("hydration", SensorDeviceClass.VOLUME),
        "calories_consumed": ("calories_consumed", SensorDeviceClass.ENERGY),
        "heart_rate_variability": ("heart_rate_variability", None),
        "daily_heart_rate_variability": ("daily_heart_rate_variability", None),
        "oxygen_saturation": ("oxygen_saturation", None),
        "daily_oxygen_saturation": ("daily_oxygen_saturation", None),
        "respiratory_rate": ("respiratory_rate", None),
        "respiratory_rate_sleep": ("respiratory_rate_sleep", None),
    }
    entries = er.async_entries_for_config_entry(entity_registry, config_entry.entry_id)
    prefix = f"{config_entry.entry_id}_"
    account_entries = {
        e.unique_id.removeprefix(prefix): e
        for e in entries
        if e.domain == "sensor" and e.unique_id.startswith(prefix)
    }
    for key, (translation_key, device_class) in expected.items():
        entry = account_entries[key]
        assert entry.translation_key == translation_key, key
        assert entry.original_device_class == device_class, key
    assert len(account_entries) == len(expected)


async def test_sensor_empty_rollup(
    hass: HomeAssistant,
    mock_google_health_client: AsyncMock,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test rollup sensors when the rollup endpoints return no data."""
    mock_google_health_client.steps.today.return_value = None
    mock_google_health_client.distance.today.return_value = None
    mock_google_health_client.active_energy_burned.today.return_value = None
    mock_google_health_client.total_calories.today.return_value = None
    mock_google_health_client.floors.today.return_value = None
    mock_google_health_client.hydration_log.today.return_value = None
    mock_google_health_client.nutrition_log.today.return_value = None

    assert await integration_setup()

    steps_state = hass.states.get("sensor.google_health_plus_steps")
    assert steps_state is not None
    assert steps_state.state == "0"

    distance_state = hass.states.get("sensor.google_health_plus_distance")
    assert distance_state is not None
    assert distance_state.state == "0.0"

    active_calories_state = hass.states.get("sensor.google_health_plus_active_calories")
    assert active_calories_state is not None
    assert active_calories_state.state == "0.0"

    total_calories_state = hass.states.get("sensor.google_health_plus_total_calories")
    assert total_calories_state is not None
    assert total_calories_state.state == "0.0"

    floors_state = hass.states.get("sensor.google_health_plus_floors")
    assert floors_state is not None
    assert floors_state.state == "0"

    hydration_state = hass.states.get("sensor.google_health_plus_water_intake")
    assert hydration_state is not None
    assert hydration_state.state == "0.0"

    calories_consumed_state = hass.states.get(
        "sensor.google_health_plus_calories_consumed"
    )
    assert calories_consumed_state is not None
    assert calories_consumed_state.state == "0.0"


async def test_sensor_empty_sleep(
    hass: HomeAssistant,
    mock_google_health_client: AsyncMock,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test sleep sensors when the sleep endpoint returns no data."""
    mock_google_health_client.sleep.list.return_value = MagicMock(data_points=[])

    assert await integration_setup()

    time_asleep_state = hass.states.get("sensor.google_health_plus_time_asleep")
    assert time_asleep_state is not None
    assert time_asleep_state.state == "unknown"


@pytest.mark.parametrize(
    ("unit_system", "expected_sensors"),
    [
        pytest.param(
            METRIC_SYSTEM,
            {
                "sensor.google_health_plus_weight": (pytest.approx(80.0), "kg"),
                "sensor.google_health_plus_distance": (pytest.approx(5.0), "km"),
                "sensor.google_health_plus_water_intake": (pytest.approx(2.5), "L"),
            },
            id="metric",
        ),
        pytest.param(
            US_CUSTOMARY_SYSTEM,
            {
                "sensor.google_health_plus_weight": (
                    pytest.approx(176.37, abs=1e-2),
                    "lb",
                ),
                "sensor.google_health_plus_distance": (
                    pytest.approx(3.11, abs=1e-2),
                    "mi",
                ),
                "sensor.google_health_plus_water_intake": (
                    pytest.approx(84.54, abs=1e-1),
                    "fl. oz.",
                ),
            },
            id="us_customary",
        ),
    ],
)
@pytest.mark.usefixtures("mock_google_health_client")
async def test_sensor_unit_conversions(
    hass: HomeAssistant,
    integration_setup: Callable[[], Awaitable[bool]],
    unit_system: UnitSystem,
    expected_sensors: dict[str, tuple[Any, str]],
) -> None:
    """Test sensors dynamically convert states and units under different unit systems."""
    hass.config.units = unit_system

    assert await integration_setup()

    for entity_id, (expected_state, expected_unit) in expected_sensors.items():
        state = hass.states.get(entity_id)
        assert state is not None
        assert float(state.state) == expected_state
        assert state.attributes.get("unit_of_measurement") == expected_unit


@pytest.mark.parametrize(
    "scopes",
    [[HealthApiScope.PROFILE_READ, HealthApiScope.SETTINGS_READ]],
    indirect=True,
)
@pytest.mark.usefixtures("mock_google_health_client")
async def test_device_sensor_via_device_id(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test a paired device is linked to the account device via via_device_id.

    Only the profile and settings scopes are granted so the account device
    can only come from the up-front registration, not from account-level
    sensors that scopes outside of this test would also create.
    """
    with patch("custom_components.google_health_plus._PLATFORMS", [Platform.SENSOR]):
        assert await integration_setup()

    account_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, config_entry.entry_id), config_entry.entry_id
    )
    assert account_device is not None

    paired_device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "watch_123"), config_entry.entry_id
    )
    assert paired_device is not None
    assert paired_device.via_device_id == account_device.id


@pytest.mark.usefixtures("mock_google_health_client")
async def test_metrics_sensors(
    hass: HomeAssistant,
    mock_google_health_client: AsyncMock,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test extended metric sensors (HRV, SpO2, respiratory rate)."""

    def _point(model: object) -> MagicMock:
        return MagicMock(data_points=[MagicMock(data=model)])

    mock_google_health_client.heart_rate_variability.list.return_value = _point(
        HeartRateVariability.from_dict(
            {
                "sampleTime": {"physicalTime": "2026-08-13T06:00:00Z"},
                "rootMeanSquareOfSuccessiveDifferencesMilliseconds": 42.5,
            }
        )
    )
    mock_google_health_client.daily_heart_rate_variability.list.return_value = _point(
        DailyHeartRateVariability.from_dict(
            {
                "date": {"year": 2026, "month": 8, "day": 13},
                "averageHeartRateVariabilityMilliseconds": 38.0,
            }
        )
    )
    mock_google_health_client.oxygen_saturation.list.return_value = _point(
        OxygenSaturation.from_dict(
            {
                "sampleTime": {"physicalTime": "2026-08-13T06:00:00Z"},
                "percentage": 97.0,
            }
        )
    )
    mock_google_health_client.daily_oxygen_saturation.list.return_value = _point(
        DailyOxygenSaturation.from_dict(
            {
                "date": {"year": 2026, "month": 8, "day": 13},
                "averagePercentage": 96.5,
                "lowerBoundPercentage": 94.0,
                "upperBoundPercentage": 98.0,
            }
        )
    )
    mock_google_health_client.daily_respiratory_rate.list.return_value = _point(
        DailyRespiratoryRate.from_dict(
            {"date": {"year": 2026, "month": 8, "day": 13}, "breathsPerMinute": 14.2}
        )
    )
    mock_google_health_client.respiratory_rate_sleep_summary.list.return_value = _point(
        RespiratoryRateSleepSummary.from_dict(
            {
                "sampleTime": {"physicalTime": "2026-08-13T06:00:00Z"},
                "fullSleepStats": {"breathsPerMinute": 13.8},
            }
        )
    )

    assert await integration_setup()

    expected_sensors = {
        "sensor.google_health_plus_heart_rate_variability": ("42.5", "ms"),
        "sensor.google_health_plus_daily_heart_rate_variability": ("38.0", "ms"),
        "sensor.google_health_plus_oxygen_saturation": ("97.0", "%"),
        "sensor.google_health_plus_daily_oxygen_saturation": ("96.5", "%"),
        "sensor.google_health_plus_respiratory_rate": ("14.2", "breaths/min"),
        "sensor.google_health_plus_sleep_respiratory_rate": ("13.8", "breaths/min"),
    }
    for entity_id, (expected_state, expected_unit) in expected_sensors.items():
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == expected_state
        assert state.attributes.get("unit_of_measurement") == expected_unit


@pytest.mark.usefixtures("mock_google_health_client")
async def test_sleep_timestamp_sensors(
    hass: HomeAssistant,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test bedtime and wake time sensors from the sleep session interval."""
    assert await integration_setup()

    bedtime = hass.states.get("sensor.google_health_plus_bedtime")
    assert bedtime is not None
    assert bedtime.state == "2026-06-29T22:00:00+00:00"

    wake_time = hass.states.get("sensor.google_health_plus_wake_time")
    assert wake_time is not None
    assert wake_time.state == "2026-06-30T06:00:00+00:00"
