from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, ATTR_DOMAIN, Platform
from homeassistant.const import Platform

from .const import DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers import device_registry

from watr import WatrApi, WatrSystem, WatrEntity
from datetime import timedelta
from pathlib import Path
import json
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SWITCH
]


@callback
def get_device_id(device: WatrEntity) -> tuple[str, str]:
    """Get device registry identifier for device."""
    return (
        DOMAIN, f"{device.id}",
    )


def token_refresh_listener(data: dict):
    p = Path(__file__).with_name("tokens.json")
    with open(p, "w") as f:
        f.write(json.dumps(data))
    _LOGGER.debug("Token refreshed!")


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    @callback
    def async_on_device_deleted(device: WatrEntity) -> None:
        _LOGGER.debug("Device deleted: %s", device)
        device = dev_reg.async_get_device({get_device_id(device)})
        if device:
            dev_reg.async_remove_device(device.id)
    dev_reg = device_registry.async_get(hass)
    username = config_entry.data["email"]
    password = config_entry.data["password"]
    force_update = False
    try:
        force_update = config_entry.data["force_update"]
    except KeyError:
        pass
    watrApi = None
    if force_update:
        # remove tokens file
        p = Path(__file__).with_name("tokens.json")
        with open(p, "w") as f:
            f.write("")
    try:
        _LOGGER.debug("Trying to use tokens!")
        p = Path(__file__).with_name("tokens.json")
        with open(p, "r") as f:
            data = json.load(f)
            accessToken = data["accessToken"]
            refreshToken = data["refreshToken"]
            _LOGGER.debug("Using tokens!")
            watrApi = WatrApi(access_token=accessToken, refresh_token=refreshToken)
            await watrApi.refresh_token()
    except Exception as e:
        _LOGGER.error(f"Failed to use tokens! - {e}")
        _LOGGER.debug("Using username and password!")
        watrApi = WatrApi(username, password)
        await watrApi.authenticate()
    _LOGGER.debug("Authenticated!")
    watr_system = WatrSystem(await watrApi.get_all_systems(), watrApi)
    _LOGGER.debug(f"Got all systems! {watr_system.data}")
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = MyCoordinator(hass, watr_system, 10)
    # config_entry.async_on_unload(config_entry.add_update_listener(update_listener))
    _LOGGER.debug("Setting up platforms")
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    watrApi.on("token_refresh", token_refresh_listener)
    _LOGGER.debug("Platforms set up!")
    await watr_system.api.refresh_token()
    stored_devices = device_registry.async_entries_for_config_entry(
        dev_reg, config_entry.entry_id
    )
    systems = watr_system.sprinkler_systems
    zones = [zone for system in systems for zone in system.zones]
    all_devices = systems + zones
    known_devices = [
        dev_reg.async_get_device({get_device_id(device)}) for device in all_devices
    ]

    for device in known_devices:
        if device not in known_devices:
            dev_reg.async_remove_device(device.id)
    return True


class MyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, watr_system: WatrSystem, interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.watr_system = watr_system

    async def _async_update_data(self) -> None:
        _LOGGER.debug("Updating data!")
        await self.watr_system.refresh()
