"""PCF8523 MicroPython RTC driver, RP2040 I2C0 GPIO8/9 at 400kHz.

Maintains UTC. Constructor is deliberately read-only to avoid erasing
battery-switch flags on every boot. Use configure_power() explicitly.
"""

def _bcd_to_int(x):
    return (x >> 4) * 10 + (x & 15)

def _int_to_bcd(x):
    return ((x // 10) << 4) | (x % 10)

def _weekday_sunday0(y, m, d):
    offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    y -= (m < 3)
    return (y + y // 4 - y // 100 + y // 400 + offsets[m-1] + d) % 7

def _valid_date(y, m, d):
    if not (2000 <= y <= 2099 and 1 <= m <= 12):
        return False
    days = (31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return 1 <= d <= days[m-1]

class PCF8523:
    ADDRESS = 0x68

    def __init__(self, i2c, address=ADDRESS):
        self.i2c, self.address = i2c, address
        if address not in i2c.scan():
            raise OSError('PCF8523 not found at 0x%02x' % address)

    def _read(self, register):
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def _write(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes((value,)))

    def registers(self):
        return list(self.i2c.readfrom_mem(self.address, 0x00, 0x10))

    def configure_power(self, mode='direct'):
        """'direct' PM=001, 'standard' PM=000. Keep status flags.

        Direct mode uses the VDD<VBAT crossing and may suit fast power removal.
        """
        if mode not in ('direct', 'standard'):
            raise ValueError('mode must be direct or standard')
        before = self._read(0x02)
        pm = 0x20 if mode == 'direct' else 0x00
        # Preserve unused bit 4 and status bits 3:2, disable battery IRQs.
        after = (before & 0x1C) | pm
        self._write(0x02, after)
        readback = self._read(0x02)
        if (readback & 0xE3) != pm:
            raise OSError('Control_3 configuration readback mismatch: 0x%02x' % readback)
        return before, readback

    def clear_battery_switch_flag(self):
        """Explicitly clear historical BSF only before starting a new test."""
        self._write(0x02, self._read(0x02) & ~0x08)

    def read_utc(self):
        data = self.i2c.readfrom_mem(self.address, 0x03, 7)
        if data[0] & 0x80:
            raise ValueError('RTC oscillator-stop flag set: sync from computer')
        second = _bcd_to_int(data[0] & 0x7F)
        minute = _bcd_to_int(data[1] & 0x7F)
        hour = _bcd_to_int(data[2] & 0x3F)
        day = _bcd_to_int(data[3] & 0x3F)
        month = _bcd_to_int(data[5] & 0x1F)
        year = 2000 + _bcd_to_int(data[6])
        if not (_valid_date(year, month, day) and 0 <= hour <= 23 and
                0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError('RTC contains an invalid date/time')
        return (year, month, day, hour, minute, second)

    def set_utc(self, year, month, day, hour, minute, second):
        if not (_valid_date(year, month, day) and 0 <= hour <= 23 and
                0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError('Invalid UTC date/time')
        c1 = self._read(0x00) & ~0x48  # 24-hour mode, T=0
        self._write(0x00, c1 | 0x20)  # STOP oscillator counter
        try:
            data = bytes((_int_to_bcd(second), _int_to_bcd(minute),
                          _int_to_bcd(hour), _int_to_bcd(day),
                          _weekday_sunday0(year, month, day),
                          _int_to_bcd(month), _int_to_bcd(year - 2000)))
            self.i2c.writeto_mem(self.address, 0x03, data)
        finally:
            self._write(0x00, c1 & ~0x20)  # resume

    def enable_second_interrupt(self):
        # CLKOUT off; second interrupt enabled on INT1.
        self._write(0x0F, 0xB8)
        self._write(0x01, 0x00)
        c1 = self._read(0x00)
        self._write(0x00, (c1 & ~0x68) | 0x04)
