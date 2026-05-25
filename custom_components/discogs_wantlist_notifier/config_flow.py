from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONDITION_MEDIA_VALUES,
    CONDITION_SLEEVE_VALUES,
    CONF_MEDIA_CONDITION,
    CONF_NOTIFICATION_ENTITY,
    CONF_SLEEVE_CONDITION,
    CONF_TOKEN,
    DEFAULT_MEDIA_CONDITION,
    DEFAULT_SLEEVE_CONDITION,
    DOMAIN,
)
from .discogs_client import validate_token

_LOGGER = logging.getLogger(__name__)


class DiscogsWantlistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            token = user_input[CONF_TOKEN]
            try:
                valid = await self.hass.async_add_executor_job(
                    validate_token, token
                )
                if not valid:
                    errors["base"] = "invalid_token"
            except Exception:
                _LOGGER.exception("Unexpected error during token validation")
                errors["base"] = "cannot_connect"
            if not errors:
                return self.async_create_entry(
                    title="Discogs Wantlist Notifier",
                    data={CONF_TOKEN: token},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MEDIA_CONDITION,
                        default=self.config_entry.options.get(
                            CONF_MEDIA_CONDITION, DEFAULT_MEDIA_CONDITION
                        ),
                    ): vol.In(CONDITION_MEDIA_VALUES),
                    vol.Required(
                        CONF_SLEEVE_CONDITION,
                        default=self.config_entry.options.get(
                            CONF_SLEEVE_CONDITION, DEFAULT_SLEEVE_CONDITION
                        ),
                    ): vol.In(CONDITION_SLEEVE_VALUES),
                    vol.Required(
                        CONF_NOTIFICATION_ENTITY,
                        default=self.config_entry.options.get(
                            CONF_NOTIFICATION_ENTITY
                        ),
                    ): selector.EntitySelector({"domain": "notify"}),
                }
            ),
        )
