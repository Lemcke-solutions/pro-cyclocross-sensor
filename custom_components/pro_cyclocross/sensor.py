from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import date
from pathlib import Path

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import DOMAIN

RACES_FILE = Path(__file__).parent / "cyclocross_races.json"

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

SERIES_LABELS = {
    "superprestige": "Superprestige",
    "world_cup": "UCI World Cup",
    "x2o_trofee": "X2O Trofee",
    "hg_cross": "HG Cross",
    "world_championships": "UCI World Championships",
}


def _load_races(path: Path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("races", [])
    except FileNotFoundError:
        _LOGGER.warning("Races file not found: %s", path)
        return []
    except (json.JSONDecodeError, OSError) as err:
        _LOGGER.error("Failed to load races file %s: %s", path, err)
        return []


def _resolve_name(name: str | dict, lang: str) -> str:
    if isinstance(name, str):
        return name
    return name.get(lang) or name.get("en") or next(iter(name.values()), "Unknown")


def _compute_slots(races: list[dict]) -> int:
    if not races:
        return 1
    return max(Counter(r["date"] for r in races).values(), default=1)


def _current_slots(races: list[dict], today: date, n: int) -> list[dict | None]:
    current = [r for r in races if date.fromisoformat(r["date"]) == today]
    return current[:n] + [None] * (n - len(current))


def _next_slots(races: list[dict], today: date, n: int) -> list[dict | None]:
    upcoming = [r for r in races if date.fromisoformat(r["date"]) > today]
    upcoming.sort(key=lambda r: date.fromisoformat(r["date"]))
    return upcoming[:n] + [None] * (n - len(upcoming))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    races = await hass.async_add_executor_job(_load_races, RACES_FILE)
    if not races:
        _LOGGER.warning(
            "No races loaded from %s — place cyclocross_races.json in the "
            "integration directory and reload the integration",
            RACES_FILE,
        )

    device_info_by_series: dict[str, DeviceInfo] = {
        series: DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{series}")},
            name=f"Pro Cyclocross — {SERIES_LABELS.get(series, series)}",
            manufacturer="Lemcke Solutions",
            model="Race Calendar",
        )
        for series in {r.get("series", "other") for r in races}
    }

    groups: dict[str, list[dict]] = {}
    for race in races:
        groups.setdefault(race.get("series", "other"), []).append(race)

    sensors: list[RaceSlotSensor] = []
    for series, group_races in groups.items():
        n_slots = _compute_slots(group_races)
        _LOGGER.debug(
            "Series %s: %d race(s), %d slot(s)", series, len(group_races), n_slots
        )
        for status in ("current", "next"):
            for slot in range(1, n_slots + 1):
                sensors.append(
                    RaceSlotSensor(
                        hass=hass,
                        entry=entry,
                        device_info=device_info_by_series[series],
                        status=status,
                        series=series,
                        slot=slot,
                        races=group_races,
                        n_slots=n_slots,
                    )
                )

    async_add_entities(sensors)

    async def _midnight_update(_now) -> None:
        for sensor in sensors:
            sensor.async_write_ha_state()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight_update, hour=0, minute=0, second=0)
    )


class RaceSlotSensor(SensorEntity):
    _attr_should_poll = False
    _attr_icon = "mdi:bike"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_info: DeviceInfo,
        status: str,
        series: str,
        slot: int,
        races: list[dict],
        n_slots: int,
    ) -> None:
        self._hass = hass
        self._status = status
        self._series = series
        self._slot = slot
        self._races = races
        self._n_slots = n_slots

        base = f"{status}_cx_{series}_{slot}"
        self.entity_id = f"sensor.{base}"
        self._attr_unique_id = f"{entry.entry_id}_{base}"
        self._attr_device_info = device_info

    def _assigned_race(self) -> dict | None:
        today = dt_util.now().date()
        if self._status == "current":
            slots = _current_slots(self._races, today, self._n_slots)
        else:
            slots = _next_slots(self._races, today, self._n_slots)
        return slots[self._slot - 1]

    @property
    def name(self) -> str:
        race = self._assigned_race()
        if race is None:
            return f"{self._status.title()} {SERIES_LABELS.get(self._series, self._series)} {self._slot}"
        return _resolve_name(race["name"], self._hass.config.language)

    @property
    def native_value(self) -> int | None:
        race = self._assigned_race()
        if race is None:
            return None
        today = dt_util.now().date()
        race_date = date.fromisoformat(race["date"])
        if self._status == "current":
            return 0
        return (race_date - today).days

    @property
    def extra_state_attributes(self) -> dict:
        race = self._assigned_race()
        if race is None:
            return {}
        lang = self._hass.config.language
        return {
            "race_name": _resolve_name(race["name"], lang),
            "series": race.get("series"),
            "location": race.get("location"),
            "date": race["date"],
        }
