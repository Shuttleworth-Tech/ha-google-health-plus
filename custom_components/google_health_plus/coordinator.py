"""Coordinators for Google Health."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, override

from google_health_api import GoogleHealthApi
from google_health_api.exceptions import (
    GoogleHealthApiError,
    HealthApiForbiddenException,
    HealthAuthException,
)
from google_health_api.model import (
    ActiveEnergyBurnedRollupValue,
    BodyFat,
    CaloriesInHeartRateZoneRollupValue,
    DailyHeartRateVariability,
    DailyHeartRateZones,
    DailyOxygenSaturation,
    DailyRespiratoryRate,
    DailyRestingHeartRate,
    DailySleepTemperatureDerivations,
    DistanceRollupValue,
    FloorsRollupValue,
    HeartRateVariability,
    HydrationLogRollupValue,
    NutritionLogRollupValue,
    OxygenSaturation,
    PairedDevice,
    RespiratoryRateSleepSummary,
    Sleep,
    StepsRollupValue,
    TimeInHeartRateZoneRollupValue,
    TotalCaloriesRollupValue,
    Weight,
)

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

if TYPE_CHECKING:
    from . import GoogleHealthConfigEntry

_LOGGER = logging.getLogger(__name__)

POLLING_INTERVAL = timedelta(minutes=15)
BODY_POLLING_INTERVAL = timedelta(hours=1)
DEVICE_POLLING_INTERVAL = timedelta(hours=1)
DEFAULT_PAGE_SIZE = 1


@dataclass
class GoogleHealthActivityData:
    """Class to hold activity data."""

    steps: StepsRollupValue | None = None
    distance: DistanceRollupValue | None = None
    active_energy_burned: ActiveEnergyBurnedRollupValue | None = None
    total_calories: TotalCaloriesRollupValue | None = None
    floors: FloorsRollupValue | None = None
    time_in_heart_rate_zones: TimeInHeartRateZoneRollupValue | None = None
    calories_in_heart_rate_zones: CaloriesInHeartRateZoneRollupValue | None = None


@dataclass
class GoogleHealthBodyData:
    """Class to hold body measurements."""

    weight: Weight | None = None
    resting_heart_rate: DailyRestingHeartRate | None = None
    body_fat: BodyFat | None = None
    heart_rate_zones: DailyHeartRateZones | None = None


class GoogleHealthDataUpdateCoordinator[_DataT](DataUpdateCoordinator[_DataT]):
    """Base coordinator for Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        name: str,
        update_interval: timedelta,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api_client
        super().__init__(
            hass,
            logger,
            name=name,
            update_interval=update_interval,
            config_entry=entry,
        )

    @override
    async def _async_update_data(self) -> _DataT:
        """Fetch data from API."""
        try:
            return await self._async_fetch_data()
        except (HealthAuthException, HealthApiForbiddenException) as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_error",
            ) from err
        except GoogleHealthApiError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
            ) from err

    async def _async_fetch_data(self) -> _DataT:
        """Fetch data from API."""
        raise NotImplementedError


class GoogleHealthActivityCoordinator(
    GoogleHealthDataUpdateCoordinator[GoogleHealthActivityData]
):
    """Coordinator to fetch activity data from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_activity",
            update_interval=POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> GoogleHealthActivityData:
        """Fetch activity rollups for today.

        Queries the daily rollup endpoints in parallel using Home Assistant's
        local time zone to aggregate steps, distance, active calories, total
        calories, and floors. If no data points exist for today yet, the API
        returns None, which the sensors default to 0.
        """
        (
            steps_rollup,
            distance_rollup,
            active_energy_rollup,
            total_calories_rollup,
            floors_rollup,
            time_in_zone_rollup,
            calories_in_zone_rollup,
        ) = await asyncio.gather(
            self.api.steps.today(self.hass.config.time_zone),
            self.api.distance.today(self.hass.config.time_zone),
            self.api.active_energy_burned.today(self.hass.config.time_zone),
            self.api.total_calories.today(self.hass.config.time_zone),
            self.api.floors.today(self.hass.config.time_zone),
            self.api.time_in_heart_rate_zone.today(self.hass.config.time_zone),
            self.api.calories_in_heart_rate_zone.today(self.hass.config.time_zone),
        )

        steps = steps_rollup.data if steps_rollup else None
        distance = distance_rollup.data if distance_rollup else None
        active_energy_burned = (
            active_energy_rollup.data if active_energy_rollup else None
        )
        total_calories = total_calories_rollup.data if total_calories_rollup else None
        floors = floors_rollup.data if floors_rollup else None

        return GoogleHealthActivityData(
            steps=steps,
            distance=distance,
            active_energy_burned=active_energy_burned,
            total_calories=total_calories,
            floors=floors,
            time_in_heart_rate_zones=time_in_zone_rollup.data
            if time_in_zone_rollup
            else None,
            calories_in_heart_rate_zones=calories_in_zone_rollup.data
            if calories_in_zone_rollup
            else None,
        )


class GoogleHealthBodyCoordinator(
    GoogleHealthDataUpdateCoordinator[GoogleHealthBodyData]
):
    """Coordinator to fetch body measurements from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_body",
            update_interval=BODY_POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> GoogleHealthBodyData:
        """Fetch latest body weight, resting heart rate, and body fat in parallel."""
        # The Google Health API returns data points sorted by interval start time
        # in descending order (newest first). Querying with page_size=1 and grabbing
        # the first element is sufficient to fetch the most recent measurement.
        weight_result, hr_result, body_fat_result, zones_result = await asyncio.gather(
            self.api.weight.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_resting_heart_rate.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.body_fat.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_heart_rate_zones.list(page_size=DEFAULT_PAGE_SIZE),
        )

        weight = (
            weight_result.data_points[0].data if weight_result.data_points else None
        )
        resting_heart_rate = (
            hr_result.data_points[0].data if hr_result.data_points else None
        )
        body_fat = (
            body_fat_result.data_points[0].data if body_fat_result.data_points else None
        )

        heart_rate_zones = (
            zones_result.data_points[0].data if zones_result.data_points else None
        )
        return GoogleHealthBodyData(
            weight=weight,
            resting_heart_rate=resting_heart_rate,
            body_fat=body_fat,
            heart_rate_zones=heart_rate_zones,
        )


class GoogleHealthDeviceCoordinator(
    GoogleHealthDataUpdateCoordinator[dict[str, PairedDevice]]
):
    """Coordinator to fetch paired devices from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_devices",
            update_interval=DEVICE_POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> dict[str, PairedDevice]:
        """Fetch paired devices."""
        devices: dict[str, PairedDevice] = {}
        result = await self.api.paired_devices.list()
        async for page in result:
            for device in page.paired_devices:
                devices[device.device_id] = device
        return devices


@dataclass
class GoogleHealthMetricsData:
    """Class to hold extended health metrics."""

    heart_rate_variability: HeartRateVariability | None = None
    daily_heart_rate_variability: DailyHeartRateVariability | None = None
    oxygen_saturation: OxygenSaturation | None = None
    daily_oxygen_saturation: DailyOxygenSaturation | None = None
    daily_respiratory_rate: DailyRespiratoryRate | None = None
    respiratory_rate_sleep_summary: RespiratoryRateSleepSummary | None = None


class GoogleHealthMetricsCoordinator(
    GoogleHealthDataUpdateCoordinator[GoogleHealthMetricsData]
):
    """Coordinator to fetch extended health metrics from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_metrics",
            update_interval=BODY_POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> GoogleHealthMetricsData:
        """Fetch latest HRV, oxygen saturation, and respiratory rate in parallel."""
        # Like the body coordinator, data points are returned newest first,
        # so page_size=1 with the first element gives the most recent value.
        (
            hrv_result,
            daily_hrv_result,
            oxygen_result,
            daily_oxygen_result,
            respiratory_result,
            respiratory_sleep_result,
        ) = await asyncio.gather(
            self.api.heart_rate_variability.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_heart_rate_variability.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.oxygen_saturation.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_oxygen_saturation.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_respiratory_rate.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.respiratory_rate_sleep_summary.list(page_size=DEFAULT_PAGE_SIZE),
        )

        return GoogleHealthMetricsData(
            heart_rate_variability=(
                hrv_result.data_points[0].data if hrv_result.data_points else None
            ),
            daily_heart_rate_variability=(
                daily_hrv_result.data_points[0].data
                if daily_hrv_result.data_points
                else None
            ),
            oxygen_saturation=(
                oxygen_result.data_points[0].data if oxygen_result.data_points else None
            ),
            daily_oxygen_saturation=(
                daily_oxygen_result.data_points[0].data
                if daily_oxygen_result.data_points
                else None
            ),
            daily_respiratory_rate=(
                respiratory_result.data_points[0].data
                if respiratory_result.data_points
                else None
            ),
            respiratory_rate_sleep_summary=(
                respiratory_sleep_result.data_points[0].data
                if respiratory_sleep_result.data_points
                else None
            ),
        )


@dataclass
class GoogleHealthSleepData:
    """Class to hold sleep data."""

    sleep: Sleep | None = None
    sleep_temperature: DailySleepTemperatureDerivations | None = None


class GoogleHealthSleepCoordinator(
    GoogleHealthDataUpdateCoordinator[GoogleHealthSleepData]
):
    """Coordinator to fetch sleep data from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_sleep",
            update_interval=BODY_POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> GoogleHealthSleepData:
        """Fetch latest sleep session and sleep temperature derivation."""
        sleep_result, temp_result = await asyncio.gather(
            self.api.sleep.list(page_size=DEFAULT_PAGE_SIZE),
            self.api.daily_sleep_temperature_derivations.list(
                page_size=DEFAULT_PAGE_SIZE
            ),
        )
        sleep = sleep_result.data_points[0].data if sleep_result.data_points else None
        sleep_temperature = (
            temp_result.data_points[0].data if temp_result.data_points else None
        )
        return GoogleHealthSleepData(sleep=sleep, sleep_temperature=sleep_temperature)


@dataclass
class GoogleHealthNutritionData:
    """Class to hold hydration and nutrition data."""

    hydration: HydrationLogRollupValue | None = None
    nutrition: NutritionLogRollupValue | None = None


class GoogleHealthNutritionCoordinator(
    GoogleHealthDataUpdateCoordinator[GoogleHealthNutritionData]
):
    """Coordinator to fetch nutrition data from Google Health API."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoogleHealthConfigEntry,
        api_client: GoogleHealthApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_nutrition",
            update_interval=POLLING_INTERVAL,
            entry=entry,
            api_client=api_client,
        )

    @override
    async def _async_fetch_data(self) -> GoogleHealthNutritionData:
        """Fetch hydration and nutrition rollups for today."""
        hydration_rollup, nutrition_rollup = await asyncio.gather(
            self.api.hydration_log.today(self.hass.config.time_zone),
            self.api.nutrition_log.today(self.hass.config.time_zone),
        )

        return GoogleHealthNutritionData(
            hydration=hydration_rollup.data if hydration_rollup else None,
            nutrition=nutrition_rollup.data if nutrition_rollup else None,
        )
