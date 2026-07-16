import machine
import utime
import sys
import select
import dht

# Motor Pins (L298N)
IN1 = machine.Pin(2, machine.Pin.OUT)
IN2 = machine.Pin(3, machine.Pin.OUT)
IN3 = machine.Pin(4, machine.Pin.OUT)
IN4 = machine.Pin(5, machine.Pin.OUT)
ENA = machine.PWM(machine.Pin(6))
ENB = machine.PWM(machine.Pin(7))
ENA.freq(1000)
ENB.freq(1000)

# Ultrasonic (HC-SR04)
TRIG = machine.Pin(14, machine.Pin.OUT)
ECHO = machine.Pin(15, machine.Pin.IN)

# DHT22
DHT_PIN = 16
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))
_last_dht_read_ms = 0
_last_temp = None
_last_hum = None
DHT_MIN_INTERVAL_MS = 2000

enc_left = 0
enc_right = 0

# ---- SAFETY WATCHDOG ----
last_cmd_ms = utime.ticks_ms()
CMD_TIMEOUT_MS = 600        # auto-stop if no command for 0.6s
motors_running = False      # track if we're driving


def set_speed(speed):
    duty = int((speed / 200) * 65535)
    duty = max(0, min(65535, duty))
    ENA.duty_u16(duty)
    ENB.duty_u16(duty)


def forward(speed=150):
    IN1.value(1); IN2.value(0)
    IN3.value(1); IN4.value(0)
    set_speed(speed)


def backward(speed=150):
    IN1.value(0); IN2.value(1)
    IN3.value(0); IN4.value(1)
    set_speed(speed)


def turn_left(speed=150):
    IN1.value(0); IN2.value(1)
    IN3.value(1); IN4.value(0)
    set_speed(speed)


def turn_right(speed=150):
    IN1.value(1); IN2.value(0)
    IN3.value(0); IN4.value(1)
    set_speed(speed)


def stop_motors():
    IN1.value(0); IN2.value(0)
    IN3.value(0); IN4.value(0)
    ENA.duty_u16(0)
    ENB.duty_u16(0)


def read_distance():
    TRIG.value(0)
    utime.sleep_us(2)
    TRIG.value(1)
    utime.sleep_us(10)
    TRIG.value(0)
    timeout = utime.ticks_ms()
    while ECHO.value() == 0:
        if utime.ticks_diff(utime.ticks_ms(), timeout) > 30:
            return -1.0
    start = utime.ticks_us()
    while ECHO.value() == 1:
        if utime.ticks_diff(utime.ticks_ms(), timeout) > 30:
            return -1.0
    end = utime.ticks_us()
    duration = utime.ticks_diff(end, start)
    distance = (duration * 0.0343) / 2
    return round(distance, 1)


def read_dht22():
    global _last_dht_read_ms, _last_temp, _last_hum
    now = utime.ticks_ms()
    if _last_temp is not None and utime.ticks_diff(now, _last_dht_read_ms) < DHT_MIN_INTERVAL_MS:
        return _last_temp, _last_hum
    try:
        dht_sensor.measure()
        _last_temp = dht_sensor.temperature()
        _last_hum = dht_sensor.humidity()
        _last_dht_read_ms = now
    except OSError:
        return None, None
    return _last_temp, _last_hum


def handle_command(cmd):
    global enc_left, enc_right, last_cmd_ms, motors_running
    cmd = cmd.strip()
    last_cmd_ms = utime.ticks_ms()   # <-- watchdog: reset timer on ANY command
    if cmd.startswith("CMD:FORWARD"):
        parts = cmd.split(":")
        speed = int(parts[2]) if len(parts) > 2 else 150
        forward(speed); motors_running = True
        print("OK:FORWARD")
    elif cmd.startswith("CMD:BACKWARD"):
        parts = cmd.split(":")
        speed = int(parts[2]) if len(parts) > 2 else 150
        backward(speed); motors_running = True
        print("OK:BACKWARD")
    elif cmd.startswith("CMD:LEFT"):
        parts = cmd.split(":")
        speed = int(parts[2]) if len(parts) > 2 else 150
        turn_left(speed); motors_running = True
        print("OK:LEFT")
    elif cmd.startswith("CMD:RIGHT"):
        parts = cmd.split(":")
        speed = int(parts[2]) if len(parts) > 2 else 150
        turn_right(speed); motors_running = True
        print("OK:RIGHT")
    elif cmd.startswith("CMD:STOP"):
        stop_motors(); motors_running = False
        print("OK:STOP")
    elif cmd == "CMD:SONAR":
        print("DIST:" + str(read_distance()))
    elif cmd == "CMD:DHT":
        temp, hum = read_dht22()
        if temp is None:
            print("ERR:DHT_READ_FAILED")
        else:
            print("DHT:" + str(temp) + ":" + str(hum))
    elif cmd == "CMD:ENCODERS":
        print("ENC:" + str(enc_left) + ":" + str(enc_right))
    elif cmd == "CMD:RESET_ENC":
        enc_left = 0
        enc_right = 0
        print("OK:RESET")


print("Sahayak Pico 2W Ready (watchdog active)")

# Non-blocking input setup
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
buf = ""

while True:
    try:
        # Non-blocking read: only read if a char is waiting
        if poller.poll(10):        # wait up to 10ms for input
            char = sys.stdin.read(1)
            if char:
                buf += char
                if "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    if line.strip():
                        handle_command(line)

        # ---- WATCHDOG: auto-stop if no command recently ----
        if motors_running and utime.ticks_diff(utime.ticks_ms(), last_cmd_ms) > CMD_TIMEOUT_MS:
            stop_motors()
            motors_running = False
            print("SAFETY:AUTO_STOP")
    except Exception as e:
        print("ERR:" + str(e))
        buf = ""