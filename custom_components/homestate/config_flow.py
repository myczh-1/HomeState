"""Config flow for HomeState."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import CONF_API_URL, DEFAULT_API_URL, DOMAIN


class HomeStateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeState."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the API URL is reachable
            api_url = user_input.get(CONF_API_URL, DEFAULT_API_URL)
            # TODO: add actual health check against /api/health
            return self.async_create_entry(
                title="HomeState",
                data={CONF_API_URL: api_url},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
                }
            ),
            errors=errors,
        )
