import serial

# ser = serial.Serial('/tmp/scale_rx', 9600)
ser = serial.Serial('/dev/ttyUSB0', 9600)
buffer = ""

while True:
    data = ser.read(1)

    if not data:
        continue

    byte = data[0]

    if byte == 2:  # STX
        buffer = ""
        continue

    elif byte == 13:  # CR
        if buffer:
            parts = buffer.strip().split()
            print(parts)

        buffer = ""
        continue

    else:
        buffer += chr(byte)