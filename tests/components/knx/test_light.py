"""Test KNX light."""

from homeassistant.components.knx import KNX_ADDRESS, SupportedPlatforms
from homeassistant.components.knx.schema import LightSchema
from homeassistant.const import CONF_NAME


async def test_light_brightness(hass, knx):
    """Test that a turn_on with unsupported attribute turns a light on."""
    name_onoff = "knx_no_brightness"
    name_brightness = "knx_with_brightness"
    name_color = "knx_with_color"
    name_white = "knx_with_white"
    name_colortemp = "knx_with_colortemp"
    entity_onoff = "light." + name_onoff
    entity_brightness = "light." + name_brightness
    entity_color = "light." + name_color
    entity_white = "light." + name_white
    entity_colortemp = "light." + name_colortemp
    ga_onoff = "1/1/8"
    ga_brightness = "1/1/10"
    ga_color = "1/1/12"
    ga_rgbw_onoff = "1/1/13"
    ga_rgbw = "1/1/14"
    ga_colortemp = "1/1/16"
    await knx.setup_integration(
        {
            SupportedPlatforms.LIGHT.value: [
                {
                    CONF_NAME: name_onoff,
                    KNX_ADDRESS: ga_onoff,
                },
                {
                    CONF_NAME: name_brightness,
                    KNX_ADDRESS: "1/1/9",
                    LightSchema.CONF_BRIGHTNESS_ADDRESS: ga_brightness,
                },
                {
                    CONF_NAME: name_color,
                    KNX_ADDRESS: "1/1/11",
                    LightSchema.CONF_COLOR_ADDRESS: ga_color,
                },
                {
                    CONF_NAME: name_white,
                    KNX_ADDRESS: ga_rgbw_onoff,
                    LightSchema.CONF_RGBW_ADDRESS: ga_rgbw,
                },
                {
                    CONF_NAME: name_colortemp,
                    KNX_ADDRESS: "1/1/15",
                    LightSchema.CONF_COLOR_TEMP_ADDRESS: ga_colortemp,
                },
            ]
        },
    )
    # check count of defined lights
    assert len(hass.states.async_all()) == 5

    # Turn on simple lamp
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": entity_onoff}, blocking=True
    )
    await knx.assert_write(ga_onoff, True)
    # Turn off simple lamp
    await hass.services.async_call(
        "light", "turn_off", {"entity_id": entity_onoff}, blocking=True
    )
    await knx.assert_write(ga_onoff, False)

    for entity, attr, value, ga, payload in [
        [entity_brightness, "brightness", 100, ga_brightness, (100,)],
        [entity_color, "color_name", "blue", ga_color, (0x00, 0x00, 0xFF)],
        # white value is removed because of light supports rgb
        [entity_white, "white_value", 88, ga_rgbw_onoff, True],
        [entity_colortemp, "color_temp", 96, ga_colortemp, (23, 112)],
    ]:
        # Turn on with specific attribute on lamp which supports specific attribute
        # Only the specific telegram is send; this implicitly switches the lamp on
        await knx.assert_telegram_count(0)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity, attr: value},
            blocking=True,
        )
        await knx.assert_write(ga, payload)

    for attr, value in [
        ["brightness", 100],
        ["color_name", "blue"],
        ["white_value", 88],
        ["color_temp", 88],
    ]:
        # Turn on with specific attribute on simple lamp
        await knx.assert_telegram_count(0)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": entity_onoff, attr: value},
            blocking=True,
        )
        await knx.assert_write(ga_onoff, True)
        await hass.services.async_call(
            "light", "turn_off", {"entity_id": entity_onoff}, blocking=True
        )
        await knx.assert_write(ga_onoff, False)


async def test_light_multi_change(hass, knx):
    """Test that a change on an attribute changes only that attribute."""
    ga_onoff = "1/1/8"
    ga_onoff2 = "1/1/9"
    ga_brightness = "1/1/10"
    ga_color = "1/1/12"
    ga_rgbw = "1/1/14"
    ga_colortemp = "1/1/16"
    await knx.setup_integration(
        {
            SupportedPlatforms.LIGHT.value: [
                {
                    CONF_NAME: "lamp1",
                    KNX_ADDRESS: ga_onoff,
                    LightSchema.CONF_BRIGHTNESS_ADDRESS: ga_brightness,
                    LightSchema.CONF_COLOR_ADDRESS: ga_color,
                    LightSchema.CONF_COLOR_TEMP_ADDRESS: ga_colortemp,
                },
                {
                    CONF_NAME: "lamp2",
                    KNX_ADDRESS: ga_onoff2,
                    LightSchema.CONF_BRIGHTNESS_ADDRESS: ga_brightness,
                    LightSchema.CONF_RGBW_ADDRESS: ga_rgbw,
                    LightSchema.CONF_COLOR_TEMP_ADDRESS: ga_colortemp,
                },
            ]
        },
    )
    # check count of defined lights
    assert len(hass.states.async_all()) == 2

    for entity, test_ga, test_payload in [
        ["lamp1", ga_color, (0, 0, 255)],
        ["lamp2", ga_rgbw, (0, 0, 255, 0, 0, 15)],
    ]:
        # Turn on lamp by setting color
        await knx.assert_telegram_count(0)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": f"light.{entity}", "color_name": "blue"},
            blocking=True,
        )
        await knx.assert_write(test_ga, test_payload)

        # Change brightness
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": f"light.{entity}", "brightness": 75},
            blocking=True,
        )

        await knx.assert_write(ga_brightness, (75,))

    for attribute, value, test_ga, test_payload in [
        ["color_name", "red", ga_color, (0xFF, 0x00, 0x00)],
        # color_temp is converted to color address in color_mode rgb
        ["color_temp", 77, ga_color, (187, 209, 255)],
        ["brightness", 55, ga_brightness, (55,)],
    ]:
        # Change attribute
        await knx.assert_telegram_count(0)
        await hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": "light.lamp1", attribute: value},
            blocking=True,
        )
        await knx.assert_write(test_ga, test_payload)
