# toleransi 300 + berat sama dalam waktu 5 detik
import serial
import time

try:
    ser = serial.Serial(port="/tmp/scale_rx", baudrate=9600, timeout=1)

    last_weight = None
    start_time = None
    toleransi = 300
    sudah_stabil = False

    buf = ""

    while True:
        data = ser.read(1).decode(errors="ignore")

        if not data:
            continue

        # STX
        if ord(data) == 2:
            buf = ""
            continue

        # CR (end frame)
        elif ord(data) == 13:
            frame = buf.strip()
            parts = frame.split()

            if len(parts) >= 3:
                try:
                    berat = int(parts[1])
                    # print("Berat:", berat)

                    # =========================
                    # LOGIKA STABIL
                    # =========================

                    if last_weight is None:
                        last_weight = berat
                        start_time = time.time()

                    if abs(berat - last_weight) <= toleransi:
                        if not sudah_stabil and (time.time() - start_time >= 5):
                            print("🔥 timbangan stabil")
                            sudah_stabil = True
                    else:
                        # reset kalau keluar toleransi
                        last_weight = berat
                        start_time = time.time()
                        sudah_stabil = False

                    # reset sistem jika berat turun hampir nol (truk keluar)
                    if berat < 100:
                        sudah_stabil = False
                        last_weight = None
                        start_time = None

                except ValueError:
                    pass

            buf = ""

        else:
            buf += data

except serial.SerialException as e:
    print("Tidak bisa membuka port:", e)