import json, time, sys, argparse
import serial
import serial.tools.list_ports

def find_pico():
    for p in serial.tools.list_ports.comports():
        if p.vid == 0x2E8A:  # raspberry pi
            return p.device
    return None

def scale(raw, dz=20):
    v = raw - 512
    if abs(v) < dz:
        return 0.0
    s = 1 if v > 0 else -1
    return round(s * min((abs(v) - dz) / (512 - dz), 1.0), 3)

def dashboard(ser):
    btn_names = [f"SW{i+1}" for i in range(10)]
    print("\033[2J\033[H", end="")
    while True:
        try:
            line = ser.readline().decode().strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            b  = d["b"]
            j1 = d["j1"]
            j2 = d["j2"]

            print("\033[H", end="")
            print("Pico Gamepad\n")

            print("Buttons:")
            for i, (name, state) in enumerate(zip(btn_names, b)):
                print(f"  {name}: {'ON ' if state else 'off'}", end="")
                if (i + 1) % 5 == 0:
                    print()
            print()

            print(f"\nJoy1  x={scale(j1[0]):+.2f}  y={scale(j1[1]):+.2f}  btn={'ON' if j1[2] else 'off'}")
            print(f"Joy2  x={scale(j2[0]):+.2f}  y={scale(j2[1]):+.2f}  btn={'ON' if j2[2] else 'off'}")
            print("\nctrl+c to quit")

        except (json.JSONDecodeError, KeyError):
            pass
        except KeyboardInterrupt:
            break

def hid_bridge(ser):
    try:
        import vgamepad as vg
    except ImportError:
        print("pip install vgamepad first")
        sys.exit(1)

    pad = vg.VX360Gamepad()
    print("virtual gamepad active")

    btn_map = [
        vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    ]

    while True:
        try:
            line = ser.readline().decode().strip()
            if not line or line.startswith("#"):
                continue
            d = json.loads(line)
            b  = d["b"]
            j1 = d["j1"]
            j2 = d["j2"]

            pad.reset()
            for state, btn in zip(b, btn_map):
                if state:
                    pad.press_button(btn)
            if j1[2]:
                pad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB)
            if j2[2]:
                pad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB)

            pad.left_joystick(x_value_float=scale(j1[0]), y_value_float=-scale(j1[1]))
            pad.right_joystick(x_value_float=scale(j2[0]), y_value_float=-scale(j2[1]))
            pad.update()

        except (json.JSONDecodeError, KeyError):
            pass
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--hid", action="store_true")
    args = ap.parse_args()

    port = args.port or find_pico()
    if not port:
        print("couldn't find pico, use --port")
        sys.exit(1)

    print(f"connecting to {port}...")
    with serial.Serial(port, 115200, timeout=1) as ser:
        time.sleep(0.5)
        ser.reset_input_buffer()
        hid_bridge(ser) if args.hid else dashboard(ser)