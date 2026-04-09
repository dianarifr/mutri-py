import serial

ser = serial.Serial('/tmp/scale_rx', 9600)

buffer = b''

while True:
    byte = ser.read(1)

    if byte == b'\x02':  # STX
        buffer = b''

        while True:
            bdata = ser.read(1)
            if bdata == b'\r':  # CR
                break
            buffer += bdata

        try:
            berat = int(buffer.decode())
            print("Berat:", berat)
        except:
            pass