import serial
import time

try:
    # serial.Serial(port=None, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=None, xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False, inter_byte_timeout=None)
    ser = serial.Serial(port="COM3", baudrate=9600, timeout=1)
    #ser =serial.Serial(port="COM3", baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=False, rtscts=False, write_timeout=None, dsrdtr=False, inter_byte_timeout=None)

    # kirim enter 2x di awal
    #ser.write(b"\r\n")
    #ser.write(b"\r\n")

    buf = ""
    buf1 = ""
    while True:
        try:
            #data = ser.readline().decode(errors="ignore").strip()
            data = ser.read(1).decode(errors="ignore")
            #print(data)
            buf += str(ord(data))+","
            buf1 += data.strip()
            if data == "\r":
                print(buf)
                print(buf1)
                buf = ""
                buf1 = ""
            else:
                pass
                #buf += data
            #print(data, end="")
        except serial.SerialException as e:
            print("Serial error:", e)
            break

except serial.SerialException as e:
    print("Tidak bisa membuka port:", e)

# python3 .\Desktop\tes-serial4.py

# jika pemisah = ")"
# output: 48,32,32,32,32,49,52,48,32,32,32,32,48,48,13,2,41,
# 48 = "0"
# 32 = " "
# 49-57 = "1-9"
# 13 = CR / "\r"
# 2 = STX = start of text
# 41 = ")"

# jika pemisah = "\r"
# outputnya: 2,41,49,32,32,50,50,49,51,48,32,49,53,50,49,48,13,
# semua line dimulai dengan: STX lalu ")", lalu 0, lalu 2x spasi, lalu angka, lalu dipisah spasi lagi?


# kesimpulan: start 1 line bacaan = STX (ascii code 2 decimal), diakhiri dengan "\r" atau CR (ascii code 13)
