import serial
s = serial.Serial(port="COM3", baudrate=38400, bytesize=8, parity='N', stopbits=1)
s.write("\r\n".encode())
s.write("\r\n".encode())
while True:
  charIn = s.read(1).decode(errors="Ignore")
  print("--"+charIn, sep="")
# python3 .\Desktop\tes-serial.py
