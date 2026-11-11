"""UTC -> America/Los_Angeles local time (PST/PDT) for MicroPython."""
import time


def _weekday_sunday0(year, month, day):
    offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    y = year - (1 if month < 3 else 0)
    return (y + y // 4 - y // 100 + y // 400 + offsets[month - 1] + day) % 7


def _nth_sunday(year, month, n):
    first = 1 + (-_weekday_sunday0(year, month, 1)) % 7
    return first + 7 * (n - 1)


def utc_to_pacific(utc):
    """Return (local YYYY,MM,DD,hh,mm,ss), 'PST' or 'PDT'.

    Pacific DST starts 2nd Sunday in March at 10:00 UTC, and ends
    1st Sunday in November at 09:00 UTC.
    On the RP2040, MicroPython's time.mktime()/gmtime() use UTC.
    """
    year, month, day, hour, minute, second = utc
    begins = (year, 3, _nth_sunday(year, 3, 2), 10, 0, 0)
    ends = (year, 11, _nth_sunday(year, 11, 1), 9, 0, 0)
    daylight = begins <= utc < ends
    hours_west = 7 if daylight else 8
    timestamp = time.mktime((year, month, day, hour, minute, second, 0, 0))
    local = time.gmtime(timestamp - hours_west * 3600)
    return local[:6], ('PDT' if daylight else 'PST')
