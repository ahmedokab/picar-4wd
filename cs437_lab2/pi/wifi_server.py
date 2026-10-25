import json
import socket
import time

HOST = "0.0.0.0"      # listen on all interfaces
PORT = 65432          # Port to listen on (non-privileged ports are > 1023)
POWER = 30            # motor power (0-100) used for every move
BURST = 1.0           # seconds the car moves per command
MOVES = ("forward", "backward", "left", "right")

# On the Pi, drive the real car. Anywhere else (e.g. a laptop), fake the stats.
try:
    import picar_4wd as fc
    FAKE = False
    fc.start_speed_thread()
except ImportError:
    import random
    FAKE = True

state = {"direction": "stop", "speed": 0.0, "distance": 0.0}


def move(cmd):
    """Run one burst, then update speed/distance from a single reading at the end."""
    if FAKE:
        time.sleep(BURST)
        speed = POWER * 0.8 + random.uniform(-2, 2)    # rough cm/s
    else:
        drive = {"forward": fc.forward, "backward": fc.backward,
                 "left": fc.turn_left, "right": fc.turn_right}[cmd]
        drive(POWER)
        time.sleep(BURST)
        speed = fc.speed_val()                          # cm/s, read just before stopping
        fc.stop()
    state["direction"] = cmd
    state["speed"] = round(speed, 2)
    state["distance"] = round(state["distance"] + speed * BURST, 2)


def read_stats():
    if FAKE:
        temperature = round(random.uniform(40, 55), 1)
        battery = round(random.uniform(7.0, 8.4), 2)
    else:
        temperature = fc.cpu_temperature()
        battery = fc.power_read()
    return {"temperature": temperature, "battery": battery, **state}


def handle(cmd):
    if cmd in MOVES:
        move(cmd)
    elif cmd == "stop":
        if not FAKE:
            fc.stop()
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
            fc.stop()
            fc.left_rear_speed.deinit()
            fc.right_rear_speed.deinit()