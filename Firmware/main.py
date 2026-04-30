from machine import Pin, SPI
import utime
import ujson

# buttons - all wired GND -> switch -> pin, so pressed = LOW
# SW1 through SW10 in order
btn_pins = [8, 7, 5, 6, 9, 10, 13, 12, 11, 14]
buttons = [Pin(p, Pin.IN, Pin.PULL_UP) for p in btn_pins]

# joystick click buttons
joy1_btn = Pin(20, Pin.IN, Pin.PULL_UP)
joy2_btn = Pin(15, Pin.IN, Pin.PULL_UP)

# MCP3008 on SPI0
# MISO=16, SCK=17, CS=18, MOSI=19
spi = SPI(0, baudrate=1000000, polarity=0, phase=0,
          sck=Pin(17), mosi=Pin(19), miso=Pin(16))
cs = Pin(18, Pin.OUT, value=1)

def read_adc(ch):
    # standard MCP3008 single-ended read
    buf = bytearray(3)
    cmd = bytearray([0x01, 0x80 | (ch << 4), 0x00])
    cs(0)
    spi.write_readinto(cmd, buf)
    cs(1)
    return ((buf[1] & 0x03) << 8) | buf[2]

# simple debounce - track last stable state + when it changed
last_state = [1] * len(buttons)
last_change = [0] * len(buttons)
DEBOUNCE = 20  # ms

def get_buttons():
    now = utime.ticks_ms()
    result = []
    for i, b in enumerate(buttons):
        v = b.value()
        if v != last_state[i] and utime.ticks_diff(now, last_change[i]) > DEBOUNCE:
            last_state[i] = v
            last_change[i] = now
        result.append(0 if last_state[i] else 1)  # invert: pressed=1
    return result

def get_joy(x_ch, y_ch, btn):
    return [read_adc(x_ch), read_adc(y_ch), 0 if btn.value() else 1]

print("# ready")

while True:
    t = utime.ticks_ms()

    btns = get_buttons()
    j1 = get_joy(1, 0, joy1_btn)   # CH1=X, CH0=Y
    j2 = get_joy(3, 2, joy2_btn)   # CH3=X, CH2=Y

    print(ujson.dumps({"b": btns, "j1": j1, "j2": j2}))

    # try to keep ~100hz, account for how long the reads took
    elapsed = utime.ticks_diff(utime.ticks_ms(), t)
    if elapsed < 10:
        utime.sleep_ms(10 - elapsed)