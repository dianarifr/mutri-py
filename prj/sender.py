import serial
import time
import random

ser = serial.Serial('/tmp/scale_tx', 9600)

weight = 0
target = random.randint(195, 200)
fase = "naik"
stable_start = None

while True:

    if fase == "naik":
        weight += random.randint(5, 15)

        if weight >= target:
            weight = target
            fase = "stabil"
            stable_start = time.time()

    elif fase == "stabil":
        # Fluktuasi kecil ±1
        weight = target

        # Stabil
        if time.time() - stable_start > random.randint(15, 30):
            fase = "turun"

    elif fase == "turun":
        weight -= random.randint(10, 20)
        if weight <= 0:
            weight = 10
            target = random.randint(195, 200)
            fase = "naik"

    # Pastikan 3 digit
    weight_str = f"{weight:03}"

    # Frame: STX )0 XXX 00 CR
    frame_text = f")0 {weight_str} 00"
    frame = b'\x02' + frame_text.encode() + b'\r'

    ser.write(frame)

    # Tampilan debug
    print(f"STX {frame_text} CR")

    # time.sleep(0.005) # 200 data per detik
    time.sleep(0.05) # 20 data per detik