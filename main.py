"""RP2040-Zero LED clock.

Place on MicroPython device as main.py. Dependencies:
  pcf8523.py and pacific_time.py
"""
import time
from machine import I2C, Pin
import neopixel
from pcf8523 import PCF8523
from pacific_time import utc_to_pacific

I2C_SDA = 8
I2C_SCL = 9
RTC_INT = 0
LED_PIN = 1
BRIGHTNESS = 0.50
STARTUP_TEST_SECONDS = 3

LAVENDER = (181, 126, 220)
PINK = (255, 105, 180)
CYAN = (0,255,255)
OFF = (0, 0, 0)


def color_at_hour(hour):
    if hour == 5 or hour == 23:
        return LAVENDER
    if hour == 6:
        return CYAN
    return OFF


def dim(color):
    return tuple(int(x * BRIGHTNESS) for x in color)


pixels = neopixel.NeoPixel(Pin(LED_PIN, Pin.OUT), 1)

def show(color):
    pixels[0] = dim(color)
    pixels.write()

# Confirms that main.py starts after a power cycle.
print('BOOT: main.py started; 3-second cyan hardware self-test')
show(CYAN)
time.sleep(STARTUP_TEST_SECONDS)
show(OFF)

# RTC setup is not allowed to block the initial visible boot self-test.
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400_000)
rtc = PCF8523(i2c)

# Interrupt support is optional for correctness: periodic polling is authoritative.
# Keep existing 1-Hz interrupt behavior, but never rely on it exclusively.
rtc.enable_second_interrupt()
irq_pending = True

def on_second(pin):
    global irq_pending
    irq_pending = True

irq_pin = Pin(RTC_INT, Pin.IN, Pin.PULL_UP)
irq_pin.irq(trigger=Pin.IRQ_FALLING, handler=on_second)

last_read_ms = time.ticks_ms()
last_minute = None
last_error = None
last_displayed = None

while True:
    now = time.ticks_ms()
    if irq_pending or time.ticks_diff(now, last_read_ms) >= 10000:
        irq_pending = False
        last_read_ms = now
        try:
            utc = rtc.read_utc()
            local, zone = utc_to_pacific(utc)
            color = color_at_hour(local[3])
            scaled = dim(color)
            if scaled != last_displayed:
                pixels[0] = scaled
                pixels.write()
                last_displayed = scaled
            if local[:5] != last_minute:
                print('RTC UTC:', utc, '| local:', local, zone,
                      '| scheduled:', color, '| WS2812:', scaled)
                last_minute = local[:5]
            last_error = None
        except (OSError, ValueError) as exc:
            if last_displayed != OFF:
                show(OFF)
                last_displayed = OFF
            if str(exc) != last_error:
                print('RTC ERROR:', repr(exc))
                last_error = str(exc)
    time.sleep_ms(50)
