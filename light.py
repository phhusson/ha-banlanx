from __future__ import annotations

import logging

import voluptuous as vol

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import (
        ATTR_BRIGHTNESS,
        ATTR_EFFECT,
        ColorMode,
        LightEntity,
        LightEntityFeature,
        PLATFORM_SCHEMA
        )
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components import bluetooth
from bleak import BleakClient, exc

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MAC): cv.string,
})

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Awesome Light platform."""

    @callback
    def _async_discovered_device(service_info: bluetooth.BluetoothServiceInfoBleak, change: bluetooth.BluetoothChange) -> None:
        """Subscribe to bluetooth changes."""
        _LOGGER.warning("New service_info: %s", service_info.address)
        ble_device = bluetooth.async_ble_device_from_address(hass, service_info.address)
        _LOGGER.warning("Got ble device " + str(ble_device))
    # Assign configuration variables.
    # The configuration check takes care they are present.
    mac = config[CONF_MAC]
    bluetooth.async_register_callback(
        hass, _async_discovered_device, {"service_uuid": "0000ffe0-0000-1000-8000-00805f9b34fb", "connectable": True}, bluetooth.BluetoothScanningMode.ACTIVE)

    # Add devices
    add_entities([BanlanxLight(hass, mac)])

def ble_get_client(hass, address):
  device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
  if not device:
    raise Exception("Device with address {0} is not available".format(address))
    return

  client = BleakClient(device)
  return client

effects = {
        "Off": [
            "A06301BE" # Set effect to RGB control
        ],
        "Rainbow": [
            "A0630101" # Set effect type
        ],
        "Rainbow meteor": [
            "A067010A", # Set effect speed to 10/max
            "A068015E", # Set effect length
            "A0630102" # Set effect type
        ],
        "Rainbow stars": [
            "A0630103" # Set effect type
        ],
        "Rainbow spin": [
            "A067010A", # Set effect speed to 10/max
            "A0680173", # Set effect length
            "A0630104" # Set effect type
        ],
        "Red Yellow Fire": [
            "A0630105" # Set effect type
        ],
        "Red Purple Fire": [
            "A0630106" # Set effect type
        ],
        "Green Yellow Fire": [
            "A0630107" # Set effect type
        ],
        "Green Cyan Fire": [
            "A0630108" # Set effect type
        ],
        "Red Comet": [
            "A063010B" # Set effect type
        ],
        "Blue Meteor": [
            "A0630114" # Set effect type
        ],
        "Red Blue Gradual Snake": [
            "A063011A" # Set effect type
        ],
        "Cyan Wave": [
            "A0630132" # Set effect type
        ],
        "Red Yellow Wave": [
            "A0630137" # Set effect type
        ],
        "White stars": [
            "A0630150" # Set effect type
        ],
        "Blue background stars": [
            "A0630153" # Set effect type
        ],
        "Drapeau Francais": [ #"Red Blue White Snake": [
            "A0630173" # Set effect type
            "A0670108", # Set effect speed to 8/10
            "A0680121", # Set effect length
        ],
}

class BanlanxLight(LightEntity):
    def __init__(self, hass, mac) -> None:
        self._hass = hass
        self._mac = mac
        self._name = "BanlanX light"
        self._light = None
        self._state = True
        self._brightness = 255
        self._current_effect = "Off"
        self._current_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_features |= LightEntityFeature.EFFECT
        self._attr_supported_color_modes = set()
        #TODO: Handle RGB
        #self._attr_supported_color_modes.add(ColorMode.RGB)
        self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
        self._attr_unique_id = f"BanlanX_{mac}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def color_mode(self):
        return self._current_color_mode

    @property
    def brightness(self):
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state
    @property
    def supported_color_modes(self):
        return self._attr_supported_color_modes

    async def write_msg(self, data):
        _LOGGER.warning("Write message hi")
        if self._light is None:
            self._light = ble_get_client(self._hass, self._mac)
            _LOGGER.warning("Got client")
        if self._light is None:
            _LOGGER.warning("Or not")
            return
        _LOGGER.warning("Connecting")
        if not self._light.is_connected:
            _LOGGER.warning("required")
            await self._light.connect()
        _LOGGER.warning("Connected")
        await self._light.write_gatt_char("0000ffe1-0000-1000-8000-00805f9b34fb", bytes.fromhex(data))
        _LOGGER.warning("Wrote msg " + data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, -1)
        effect = kwargs.get(ATTR_EFFECT, -1)
        if effect == -1:
            effect = self._current_effect
        if brightness == -1:
            brightness = self._brightness

        _LOGGER.warning(f"Turning ON with brightness {brightness} and effects {effect}")
        # Turn on
        await self.write_msg("A0620101")
        # Set brightness level
        await self.write_msg("A06601" + format(brightness, "02X"))
        if effect != self._current_effect:
            for i in effects[effect]:
                await self.write_msg(i)

        self._current_effect = effect
        self._brightness = brightness
        self._state = True

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        await self.write_msg("A0620100")
        self._state = False

    def update(self) -> None:
        return

    @property
    def effect_list(self):
        return list(effects.keys())
    @property
    def effect(self):
        return self._current_effect

