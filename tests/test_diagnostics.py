"""Tests for the diagnostics data provided by the Google Health integration."""

from collections.abc import Awaitable, Callable
from datetime import timedelta
from unittest.mock import AsyncMock

from google_health_api.exceptions import GoogleHealthApiError
from google_health_api.model import ListDataPointResult, _ListDataPointsModel
import pytest

from custom_components.google_health_plus.const import OAUTH_SCOPES
from custom_components.google_health_plus.coordinator import POLLING_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator


@pytest.mark.freeze_time("2026-07-22 00:00:00+00:00")
@pytest.mark.usefixtures("mock_google_health_client")
async def test_diagnostics_full_data(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test diagnostics output when all coordinators have data."""
    assert await integration_setup()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics == {
        "activity_coordinator": {
            "active_energy_burned": True,
            "distance": True,
            "floors": True,
            "last_update_success": True,
            "steps": True,
            "total_calories": True,
        },
        "body_coordinator": {
            "body_fat": True,
            "last_update_success": True,
            "resting_heart_rate": True,
            "weight": True,
        },
        "config_entry": {
            "auth_implementation": "google_health_plus",
            "token": {
                "access_token": "**REDACTED**",
                "expires_at": 1784764800,
                "refresh_token": "**REDACTED**",
                "scope": " ".join(OAUTH_SCOPES),
                "token_type": "Bearer",
            },
        },
        "metrics_coordinator": {
            "daily_heart_rate_variability": False,
            "daily_oxygen_saturation": False,
            "daily_respiratory_rate": False,
            "heart_rate_variability": False,
            "last_update_success": True,
            "oxygen_saturation": False,
            "respiratory_rate_sleep_summary": False,
        },
        "sleep_coordinator": {
            "last_update_success": True,
            "sleep": True,
        },
    }


@pytest.mark.freeze_time("2026-07-22 00:00:00+00:00")
async def test_diagnostics_empty_data(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_google_health_client: AsyncMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test diagnostics output when coordinators have no data."""
    # Mock all coordinator endpoints to return None or empty data
    mock_google_health_client.steps.today.return_value = None
    mock_google_health_client.distance.today.return_value = None
    mock_google_health_client.active_energy_burned.today.return_value = None
    mock_google_health_client.total_calories.today.return_value = None
    mock_google_health_client.floors.today.return_value = None

    mock_google_health_client.weight.list.return_value = ListDataPointResult(
        _ListDataPointsModel(data_points=[])
    )
    mock_google_health_client.daily_resting_heart_rate.list.return_value = (
        ListDataPointResult(_ListDataPointsModel(data_points=[]))
    )
    mock_google_health_client.body_fat.list.return_value = ListDataPointResult(
        _ListDataPointsModel(data_points=[])
    )

    mock_google_health_client.sleep.list.return_value = ListDataPointResult(
        _ListDataPointsModel(data_points=[])
    )

    assert await integration_setup()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics == {
        "activity_coordinator": {
            "active_energy_burned": False,
            "distance": False,
            "floors": False,
            "last_update_success": True,
            "steps": False,
            "total_calories": False,
        },
        "body_coordinator": {
            "body_fat": False,
            "last_update_success": True,
            "resting_heart_rate": False,
            "weight": False,
        },
        "config_entry": {
            "auth_implementation": "google_health_plus",
            "token": {
                "access_token": "**REDACTED**",
                "expires_at": 1784764800,
                "refresh_token": "**REDACTED**",
                "scope": " ".join(OAUTH_SCOPES),
                "token_type": "Bearer",
            },
        },
        "metrics_coordinator": {
            "daily_heart_rate_variability": False,
            "daily_oxygen_saturation": False,
            "daily_respiratory_rate": False,
            "heart_rate_variability": False,
            "last_update_success": True,
            "oxygen_saturation": False,
            "respiratory_rate_sleep_summary": False,
        },
        "sleep_coordinator": {
            "last_update_success": True,
            "sleep": False,
        },
    }


@pytest.mark.freeze_time("2026-07-22 00:00:00+00:00")
async def test_diagnostics_update_failed(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_google_health_client: AsyncMock,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test diagnostics output when coordinator update fails."""
    assert await integration_setup()

    # Trigger update failure on next refresh for activity coordinator
    mock_google_health_client.steps.today.side_effect = GoogleHealthApiError(
        "API Error"
    )

    async_fire_time_changed(
        hass,
        dt_util.utcnow() + POLLING_INTERVAL + timedelta(seconds=1),
    )
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics == {
        "activity_coordinator": {
            "active_energy_burned": True,
            "distance": True,
            "floors": True,
            "last_update_success": False,
            "steps": True,
            "total_calories": True,
        },
        "body_coordinator": {
            "body_fat": True,
            "last_update_success": True,
            "resting_heart_rate": True,
            "weight": True,
        },
        "config_entry": {
            "auth_implementation": "google_health_plus",
            "token": {
                "access_token": "**REDACTED**",
                "expires_at": 1784764800,
                "refresh_token": "**REDACTED**",
                "scope": " ".join(OAUTH_SCOPES),
                "token_type": "Bearer",
            },
        },
        "metrics_coordinator": {
            "daily_heart_rate_variability": False,
            "daily_oxygen_saturation": False,
            "daily_respiratory_rate": False,
            "heart_rate_variability": False,
            "last_update_success": True,
            "oxygen_saturation": False,
            "respiratory_rate_sleep_summary": False,
        },
        "sleep_coordinator": {
            "last_update_success": True,
            "sleep": True,
        },
    }


@pytest.mark.freeze_time("2026-07-22 00:00:00+00:00")
@pytest.mark.usefixtures("mock_google_health_client")
@pytest.mark.parametrize(
    "scopes",
    [
        [
            "https://www.googleapis.com/auth/googlehealth.profile.readonly",
            "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
        ]
    ],
)
async def test_diagnostics_partial_scopes(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    integration_setup: Callable[[], Awaitable[bool]],
) -> None:
    """Test diagnostics when only a subset of scopes is authorized."""
    assert await integration_setup()

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, config_entry
    )

    assert diagnostics == {
        "activity_coordinator": {
            "active_energy_burned": True,
            "distance": True,
            "floors": True,
            "last_update_success": True,
            "steps": True,
            "total_calories": True,
        },
        "body_coordinator": None,
        "config_entry": {
            "auth_implementation": "google_health_plus",
            "token": {
                "access_token": "**REDACTED**",
                "expires_at": 1784764800,
                "refresh_token": "**REDACTED**",
                "scope": "https://www.googleapis.com/auth/googlehealth.profile.readonly"
                " https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
                "token_type": "Bearer",
            },
        },
        "metrics_coordinator": None,
        "sleep_coordinator": None,
    }
