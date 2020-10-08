"""Config flow for MPD."""

import logging

import mpd
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)

_LOGGER = logging.getLogger(__name__)


class ConnectionFailure(exceptions.HomeAssistantError):
    """Cannot connect to MPD."""


class AuthFailure(exceptions.HomeAssistantError):
    """Authentication failure."""


class MpdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for MPD."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._host = None
        self._password = None
        self._name = None
        self._port = None

    @staticmethod
    async def check_mpd_connection(data):
        """Check if connection is successful."""
        try:
            client = mpd.MPDClient()
            client.connect(data[CONF_HOST], data[CONF_PORT])
            password = data.get(CONF_PASSWORD)
            if password is not None:
                client.password(password)
        except (mpd.ConnectionError, ConnectionRefusedError) as ex:
            raise ConnectionFailure from ex
        except mpd.CommandError as ex:
            raise AuthFailure from ex
        finally:
            client.disconnect()

    async def async_step_user(self, user_input=None):
        """Handle flow initialized by user."""

        if not user_input:
            return self._show_form()

        self._host = user_input[CONF_HOST]
        self._password = user_input.get(CONF_PASSWORD)
        self._name = user_input[CONF_NAME]
        self._port = user_input[CONF_PORT]

        # TODO check if host is valid and raise exceptions if not

        # Try to connect
        try:
            await self.check_mpd_connection(user_input)
        except ConnectionFailure:
            return self._show_form({"base": "cannot_connect"})
        except AuthFailure:
            return self._show_form({"base": "invalid_auth"})
        except Exception:
            return self._show_form({"base": "unknown"})
        else:
            return self.async_create_entry(title=self._name, data=user_input)

    async def async_step_import(self, data):
        """Import configuration from YAML."""
        try:
            await self.check_mpd_connection(data)
        except ConnectionFailure:
            return self.async_abort(reason="cannot_connect")
        except AuthFailure:
            return self.async_abort(reason="invalid_auth")
        except Exception:
            return self.async_abort(reason="unknown")
        else:
            return self.async_create_entry(title=data[CONF_NAME], data=data)

    @callback
    def _show_form(self, errors=None):
        """Show form to user."""
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors if errors else {},
        )
