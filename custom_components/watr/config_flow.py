from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.data_entry_flow import FlowResult, FlowHandler
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant import exceptions
from urllib.parse import urlparse
from .const import DOMAIN
from typing import Any
from watr import WatrApi

import voluptuous as vol

DATA_SCHEMA = vol.Schema({
    vol.Required("email"): str,
    vol.Required("password"): str
})


class SqlSprinklerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_init(self, info=None) -> FlowResult:
        await self.async_step_user()

    async def async_step_user(self, info=None) -> FlowResult:
        errors = {}
        if info is not None:
            await self.async_set_unique_id(DOMAIN)
            _res = {
                "credentials": {
                    "email": info["email"],
                    "password": info["password"]
                }
            }
            return self.async_create_entry(title="Watr", data=_res)
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, info=None) -> FlowResult:
        errors = {}
        if info is not None:
            return self.async_create_entry(title="Watr", data=res)
        return self.async_show_form(
            step_id="init",
            data_schema=DATA_SCHEMA,
            errors=errors
        )
