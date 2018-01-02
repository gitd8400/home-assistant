"""
Support for Velbus covers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/cover.velbus/
"""
import logging
import asyncio
import time

import voluptuous as vol

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, SUPPORT_OPEN, SUPPORT_CLOSE,
    SUPPORT_STOP)
from homeassistant.components.velbus import DOMAIN
from homeassistant.const import (CONF_COVERS, CONF_NAME)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_CHANNEL = 'channel'
CONF_MODULE = 'module'
CONF_VMB1BL = 'is_VMB1BL'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_COVERS): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_CHANNEL): cv.positive_int,
            vol.Required(CONF_MODULE): cv.positive_int,
            vol.Optional('is_VMB1BL', default = False): cv.boolean
        }
    ])
})

DEPENDENCIES = ['velbus']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up cover controlled by Velbus."""
    velbus = hass.data[DOMAIN]
    covers = []
    covers_conf = config.get(CONF_COVERS)


    for cover in covers_conf:
        covers.append(VelbusCover(
        velbus, cover[CONF_NAME], cover[CONF_MODULE], cover[CONF_CHANNEL]))

    if not covers:
        _LOGGER.error("No covers added")
        return False

    add_devices(covers)


class VelbusCover(CoverDevice):
    """Representation a Velbus cover."""

    def __init__(self, velbus, name, module, channel):
        """Initialize the cover."""
        self._velbus = velbus
        self._name = name
        self._channel_state = True
        self._module = module
        self._channel = channel
        self.logger = logging.getLogger('velbus')

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Add listener for Velbus messages on bus."""
        def _init_velbus():
            """Initialize Velbus on startup."""
            self._velbus.subscribe(self._on_message)
            self.get_status()

        yield from self.hass.async_add_job(_init_velbus)

    def _on_message(self, message):
        import velbus
        if isinstance(message, velbus.BlindStatusMessage):
            if message.address == self._module:
                if message.channel == self._channel:
                    if message.blind_position == 0:
                        self._channel_state = message.is_up()
                        self.schedule_update_ha_state()
                    if message.blind_position == 100:
                        self._channel_state = message.is_down()
                        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE

    @property
    def should_poll(self):
        """Disable polling."""
        return False

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._channel_state

    @property
    def current_cover_position(self):
        """Return current position of cover.

        None is unknown.
        """
        return None

    def _blind_down(self, channel):
        import velbus
        message = velbus.CoverDownMessage()
        message.set_defaults(self._module)
        message.channel = channel
        self._velbus.send(message)

    def _blind_up(self, channel):
        import velbus
        message = velbus.CoverUpMessage()
        message.set_defaults(self._module)
        message.channel = channel
        self._velbus.send(message)

    def open_cover(self, **kwargs):
        """Open the cover."""
        self._blind_up(self._channel)

    def close_cover(self, **kwargs):
        """Close the cover."""
        self._blind_down(self._channel)

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        raise NotImplementedError()

    def get_status(self):
        """Retrieve current status."""
        import velbus
        message = velbus.ModuleStatusRequestMessage()
        message.set_defaults(self._module)
        message.channels = [self._channel]
        self._velbus.send(message)
