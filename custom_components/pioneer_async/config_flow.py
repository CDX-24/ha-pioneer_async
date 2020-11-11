"""Config flow for pioneer_async integration."""

import logging
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import callback

from aiopioneer import PioneerAVR
from aiopioneer.param import (
    # PARAM_IGNORED_ZONES,
    PARAM_COMMAND_DELAY,
    PARAM_MAX_SOURCE_ID,
    PARAM_MAX_VOLUME,
    PARAM_MAX_VOLUME_ZONEX,
    PARAM_POWER_ON_VOLUME_BOUNCE,
    PARAM_VOLUME_STEP_ONLY,
    PARAM_VOLUME_STEP_DELTA,
    PARAM_DEBUG_LISTENER,
    PARAM_DEBUG_RESPONDER,
    PARAM_DEBUG_UPDATER,
    PARAMS_ALL,
)

from .const import (
    DATA_SCHEMA,
    OPTIONS_DEFAULTS,
    OPTIONS_ALL,
)
from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: core.HomeAssistant, data):
    """
    Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    _LOGGER.debug(">> validate_input(%s)", data)
    try:
        pioneer = PioneerAVR(data[CONF_HOST], data[CONF_PORT])
        await pioneer.connect()
        await pioneer.query_device_info()
        await pioneer.shutdown()
        del pioneer
    except Exception as exc:  # pylint: disable=broad-except
        _LOGGER.debug("exception caught: %s", str(exc))
        raise CannotConnect  # pylint: disable=raise-missing-from

    # Return info that you want to store in the config entry.
    return data


class PioneerAVRFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Pioneer AVR config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        _LOGGER.debug(">> config.async_step_user(%s)", user_input)
        errors = {}
        if user_input is not None:
            try:
                data = await validate_input(self.hass, user_input)
                unique_id = data[CONF_HOST] + ":" + str(data[CONF_PORT])
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=unique_id, data=data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected exception: %s", str(exc))
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return PioneerAVROptionsFlowHandler(config_entry)


class PioneerAVROptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Harmony."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        _LOGGER.debug(">> options.__init__()")
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        _LOGGER.debug(">> options.async_step_init(%s)", user_input)

        entry = self.config_entry
        pioneer = self.hass.data[DOMAIN][entry.entry_id]
        default_params = pioneer.get_default_params()
        if user_input is not None:
            ## Save options and params for non-default values only
            options = {
                k: user_input[k]
                for k in OPTIONS_ALL
                if k in user_input and user_input[k] != OPTIONS_DEFAULTS[k]
            }
            params = {
                k: user_input[k]
                for k in PARAMS_ALL
                if k in user_input and user_input[k] != default_params[k]
            }
            _LOGGER.debug("options=%s, params=%s", options, params)
            return self.async_create_entry(title="", data={**options, **params})

        ## Get current set of options
        entry_options = entry.options if entry.options else {}
        options = {
            **OPTIONS_DEFAULTS,
            **default_params,
            **entry_options,
        }

        ## Build options schema
        data_schema = vol.Schema(
            {
                ## TODO: add sources option: how to ask the user for a dictionary in config flow?
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=options[CONF_SCAN_INTERVAL]
                ): int,
                vol.Optional(CONF_TIMEOUT, default=options[CONF_TIMEOUT]): vol.Coerce(
                    float
                ),
                vol.Optional(
                    PARAM_COMMAND_DELAY, default=options[PARAM_COMMAND_DELAY]
                ): vol.Coerce(float),
                vol.Optional(
                    PARAM_MAX_SOURCE_ID, default=options[PARAM_MAX_SOURCE_ID]
                ): int,
                vol.Optional(PARAM_MAX_VOLUME, default=options[PARAM_MAX_VOLUME]): int,
                vol.Optional(
                    PARAM_MAX_VOLUME_ZONEX, default=options[PARAM_MAX_VOLUME_ZONEX]
                ): int,
                vol.Optional(
                    PARAM_POWER_ON_VOLUME_BOUNCE,
                    default=options[PARAM_POWER_ON_VOLUME_BOUNCE],
                ): bool,
                vol.Optional(
                    PARAM_VOLUME_STEP_ONLY, default=options[PARAM_VOLUME_STEP_ONLY]
                ): bool,
                vol.Optional(
                    PARAM_VOLUME_STEP_DELTA, default=options[PARAM_VOLUME_STEP_DELTA]
                ): int,
                vol.Optional(
                    PARAM_DEBUG_LISTENER, default=options[PARAM_DEBUG_LISTENER]
                ): bool,
                vol.Optional(
                    PARAM_DEBUG_RESPONDER, default=options[PARAM_DEBUG_RESPONDER]
                ): bool,
                vol.Optional(
                    PARAM_DEBUG_UPDATER, default=options[PARAM_DEBUG_UPDATER]
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
