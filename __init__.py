"""Support to embed Sonos."""
from homeassistant import config_entries
from homeassistant.helpers import config_entry_flow


DOMAIN = 'sonosmanual'
#REQUIREMENTS = ['pysonos==0.0.8']


async def async_setup(hass, config):
    return True
