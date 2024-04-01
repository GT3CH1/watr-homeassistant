import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.components.switch import (PLATFORM_SCHEMA, SwitchEntity)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigType, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][config.entry_id]
    watr_system = coordinator.watr_system
    _LOGGER.debug("Refreshing data")
    await watr_system.refresh()
    _LOGGER.debug("Data refreshed")
    entities = []
    for system in watr_system.sprinkler_systems:
        _LOGGER.debug(f"Adding system: {system.name}")
        entities.append(WatrSystemSwitch(coordinator, system))
        for zone in system.zones:
            _LOGGER.debug(f"Adding zone: {zone.name}")
            entities.append(WatrZoneSwitch(coordinator, zone))

    async_add_entities(entities, True)


class WatrZoneSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, zone):
        super().__init__(coordinator)
        self._zone = zone
        self._attr_is_on = self._zone.is_on

    @property
    def name(self):
        return self._zone.name

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        await self._zone.toggle()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        await self._zone.toggle()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        # self._zone = self.coordinator.watr_system.sprinkler_systems[self._zone.system_id].zones[self._zone.id]
        _zone = None
        for system in self.coordinator.watr_system.sprinkler_systems:
            for zone in system.zones:
                if zone.id == self._zone.id:
                    _zone = zone
                    break
        self._zone = _zone
        self._attr_is_on = self._zone.is_on
        self.async_write_ha_state()


class WatrSystemSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, system):
        super().__init__(coordinator)
        self._system = system
        self._attr_is_on = self._system.enabled

    @property
    def name(self):
        return self._system.name

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        await self._system.toggle()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        await self._system.toggle()
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.id)},
            "name": self._system.name,
            "manufacturer": "Watr",
            "model": "Sprinkler System",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        # self._attr_is_on = self.coordinator.watr_system.sprinkler_systems[self._system.id].enabled
        # find system where id == self._system.id
        _sys = next(
            (system for system in self.coordinator.watr_system.sprinkler_systems if system.id == self._system.id), None)
        self._attr_is_on = _sys.enabled
        self._system = _sys
        _LOGGER.debug("Coordinator updated")
        # self._system.data["enabled"] = self._attr_is_on
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self._system.id)},
            "name": self._system.name,
            "manufacturer": "Watr",
            "model": "Sprinkler System",
        }
