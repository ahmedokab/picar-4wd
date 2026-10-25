import json
import socket
import time

HOST = "0.0.0.0"      # listen on all interfaces
PORT = 65432          # Port to listen on (non-privileged ports are > 1023)
POWER = 30            # motor power (0-100) used for every move
BURST = 1.0           # seconds the car moves per command
TURN_ANGLE = 30       # steering angle for left/right (PiCar-X max is about 30)
MOVES = ("forward", "backward", "left", "right")


CM_PER_SECOND_AT_POWER_30 = 25

try:
    from picarx import Picarx
    from robot_hat import ADC
    FAKE = False
    car = Picarx()
    battery_adc = ADC("A4")    # Robot HAT reads battery voltage on pin A4
except ImportError:
    import random
    FAKE = True

state = {"direction": "stop", "speed": 0.0, "distance": 0.0}


def move(cmd):
    """Run one burst, then update speed/distance."""
    if FAKE:
        time.sleep(BURST)
        speed = POWER * 0.8 + random.uniform(-2, 2)    # rough cm/s
    else:
        if cmd == "forward":
            car.set_dir_servo_angle(0)
            car.forward(POWER)
        elif cmd == "backward":
            car.set_dir_servo_angle(0)
            car.backward(POWER)
        elif cmd == "left":
            # The PiCar-X steers like a real car, so it turns while driving forward
            car.set_dir_servo_angle(-TURN_ANGLE)
            car.forward(POWER)
        elif cmd == "right":
            car.set_dir_servo_angle(TURN_ANGLE)
            car.forward(POWER)
        time.sleep(BURST)
        car.stop()
        car.set_dir_servo_angle(0)
        speed = CM_PER_SECOND_AT_POWER_30 * POWER / 30    # estimated cm/s
    state["direction"] = cmd
    state["speed"] = round(speed, 2)
    state["distance"] = round(state["distance"] + speed * BURST, 2)


def read_stats():
    if FAKE:
        temperature = round(random.uniform(40, 55), 1)
        battery = round(random.uniform(7.0, 8.4), 2)
    else:
        with open("/sys/class/thermal/thermal_zone0/temp") as temperature_file:
            temperature = round(int(temperature_file.read()) / 1000, 1)
        battery = round(battery_adc.read_voltage() * 3, 2)   # ADC sees 1/3 of battery voltage
    return {"temperature": temperature, "battery": battery, **state}


def handle(cmd):
    if cmd in MOVES:
        move(cmd)
    elif cmd == "stop":
        if not FAKE:
            car.stop()
            car.set_dir_servo_angle(0)
        state["direction"] = "stop"
        state["speed"] = 0.0
    elif cmd != "stats":
        return {"error": f"unknown command: {cmd}"}
    return read_stats()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    s.settimeout(1.0)     # wake up every second so Ctrl+C works (also on Windows)
    print(f"Listening on {HOST}:{PORT} ({'fake' if FAKE else 'car'} mode)")
    try:
        while True:
            try:
                client, clientInfo = s.accept()
            except socket.timeout:
                continue
            with client:
                data = client.recv(1024)
                if not data:
                    continue
                cmd = data.decode().strip().lower()
                if cmd != "stats":
                    print("server recv from:", clientInfo, cmd)
                reply = handle(cmd)
                client.sendall((json.dumps(reply) + "\r\n").encode())
    except KeyboardInterrupt:
        print("Closing socket")
    finally:
        if not FAKE:
            car.stop()
            car.set_dir_servo_angle(0)