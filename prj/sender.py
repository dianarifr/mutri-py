import serial
import time
import random

PORT = '/tmp/scale_tx'
BAUDRATE = 9600

ser = None
connected = False

last_wait_print = 0

weight = 0
target = random.randint(195, 200)

fase = "kosong"

stable_start = None
empty_start = None


# ==================================
# CONNECT SERIAL
# ==================================

def connect_serial():

    global ser
    global connected
    global last_wait_print

    while not connected:

        try:

            ser = serial.Serial(PORT, BAUDRATE)

            connected = True

            print(f"✅ Serial terhubung: {PORT}")

        except Exception:

            now = time.time()

            # anti spam log
            if now - last_wait_print >= 5:

                print(f"🟡 Menunggu serial: {PORT}")

                last_wait_print = now

            time.sleep(2)


# ==================================
# SAFE WRITE
# ==================================

def write_frame(frame):

    global connected
    global ser

    try:

        ser.write(frame)

    except Exception as e:

        print("🟡 Serial terputus:", e)

        connected = False

        try:
            ser.close()
        except:
            pass

        ser = None


# ==================================
# MAIN LOOP
# ==================================

while True:

    # reconnect kalau putus
    if not connected:

        connect_serial()

    # =========================
    # FASE KOSONG
    # =========================

    if fase == "kosong":

        weight = 0

        if empty_start is None:
            empty_start = time.time()

        # kosong 5-10 detik
        if time.time() - empty_start >= random.randint(5, 10):

            fase = "naik"

            target = random.randint(195, 200)

            empty_start = None

    # =========================
    # FASE NAIK
    # =========================

    elif fase == "naik":

        weight += random.randint(5, 15)

        if weight >= target:

            weight = target

            fase = "stabil"

            stable_start = time.time()

    # =========================
    # FASE STABIL
    # =========================

    elif fase == "stabil":

        weight = target

        # stabil 15-30 detik
        if (
            time.time() - stable_start
            >= random.randint(15, 30)
        ):

            fase = "turun"

    # =========================
    # FASE TURUN
    # =========================

    elif fase == "turun":

        weight -= random.randint(10, 20)

        if weight <= 0:

            weight = 0

            fase = "kosong"

            empty_start = time.time()

    # =========================
    # FORMAT BERAT
    # =========================

    weight_str = f"{weight:03}"

    # =========================
    # FRAME
    # =========================

    frame_text = f")0 {weight_str} 00"

    frame = (
        b'\x02'
        + frame_text.encode()
        + b'\r'
    )

    # =========================
    # WRITE
    # =========================

    write_frame(frame)

    # =========================
    # DEBUG
    # =========================

    print(
        f"[{fase.upper()}] "
        f"{frame} >> STX {frame_text} CR"
    )

    # 20 data per detik
    time.sleep(0.05)