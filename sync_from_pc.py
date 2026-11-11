"""Run on your COMPUTER with CPython.

Install: python -m pip install mpremote
Run:     python sync_from_pc.py [--port auto]
"""
import argparse
from datetime import datetime, timezone
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description='Set PCF8523 RTC from computer UTC')
    parser.add_argument('--port', default='auto',
                        help='mpremote port, e.g. auto, /dev/tty.usbmodemXXXX, COM5')
    args = parser.parse_args()

    # Always obtain UTC, independent of the computer's local timezone.
    now = datetime.now(timezone.utc)
    fields = (now.year, now.month, now.day, now.hour, now.minute, now.second)
    code = (
        'from machine import I2C, Pin; '
        'from pcf8523 import PCF8523; '
        'c = PCF8523(I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)); '
        "c.configure_power('direct'); "
        'c.set_utc(%d, %d, %d, %d, %d, %d); '
        "print('RTC UTC:', c.read_utc())" % fields
    )
    print('Sending computer UTC:', now.strftime('%Y-%m-%d %H:%M:%S UTC'))
    # exec temporarily interrupts main.py; reset starts the LED program again.
    subprocess.run([sys.executable, '-m', 'mpremote', 'connect', args.port,
                    'exec', code, 'reset'], check=True)
    print('RTC synchronized; RP2040 restarting its LED program.')


if __name__ == '__main__':
    main()
