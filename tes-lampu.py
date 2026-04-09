import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

try:
    while True:
        # Merah nyala
        ser.write(b'10\n')
        print("🔴 MERAH ON")
        time.sleep(0.5)

        # Mati
        ser.write(b'00\n')
        print("⚫ OFF")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStop test")

finally:
    ser.write(b'00\n')  # pastikan mati saat keluar
    ser.close()