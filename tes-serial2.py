import serial
import time

try:
    # serial.Serial(port=None, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=None, xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False, inter_byte_timeout=None)
    ser = serial.Serial(port="COM3", baudrate=9600, timeout=1)
    #ser =serial.Serial(port="COM3", baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False, inter_byte_timeout=None)

    # kirim enter 2x di awal
    ser.write(b"\r\n")
    ser.write(b"\r\n")

    while True:
        try:
            #data = ser.readline().decode(errors="ignore").strip()
            data = ser.read(1).decode(errors="ignore").strip()
    #        if data:
                print(data, sep="", end="")
#            else:
 #               # kalau kosong, kirim enter
  #              ser.write(b"\r\n")
   #             time.sleep(0.1)  # kasih jeda biar nggak spam
        except serial.SerialException as e:
            print("Serial error:", e)
            break

except serial.SerialException as e:
    print("Tidak bisa membuka port:", e)

# python3 .\Desktop\tes-serial2.py
