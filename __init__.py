from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, ATTR_DOMAIN, Platform
from homeassistant.const import Platform

from .const import DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from watr import WatrApi, WatrSystem
from datetime import timedelta
from pathlib import Path
import json
import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SWITCH
]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    def token_refresh_listener(data: dict):
        p = Path(__file__).with_name("tokens.json")
        with open(p, "w") as f:
            f.write(json.dumps(data))
        _LOGGER.debug("Token refreshed!")

    username = config_entry.data["email"]
    password = config_entry.data["password"]
    watrApi = None
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
        watrApi.on("token_refresh", token_refresh_listener)
        await watrApi.authenticate()
    _LOGGER.debug("Authenticated!")
    watr_system = WatrSystem(await watrApi.get_all_systems(), watrApi)
    _LOGGER.debug(f"Got all systems! {watr_system.data}")
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = MyCoordinator(hass, watr_system, 10)
    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))
    _LOGGER.debug("Setting up platforms")
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    watrApi.on("token_refresh", token_refresh_listener)
    _LOGGER.debug("Platforms set up!")
    await watr_system.api.refresh_token()
    return True


async def update_listener(hass, entry):
    _LOGGER.debug("Received an update!")
    username = entry.options.data["username"]
    password = entry.options.data["password"]
    accessToken = entry.options.data["accessToken"]
    refreshToken = entry.options.data["refreshToken"]

    if accessToken and refreshToken:
        _LOGGER.debug("Using tokens!")
        watr_api = WatrApi(accessToken=accessToken, refreshToken=refreshToken)
        await watr_api.refresh_token()
    else:
        _LOGGER.debug("Using username and password!")
        watr_api = WatrApi(username, password)
        await watr_api.login()
    _data = await watr_api.get_all_systems()
    watr_system = WatrSystem(_data, watr_api)
    sys = MyCoordinator(hass, watr_system, 10)
    hass.data[DOMAIN][entry.entry_id] = watr_system


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
