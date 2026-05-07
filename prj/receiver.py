# receiver_scale.py
import serial
import time
import threading
import requests

from lamp import LampController

class ScaleReceiver:

    def __init__(self, port="/tmp/scale_rx", baudrate=9600):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=1)
        # self.lamp = LampController('/tmp/usb_virtual_rx') --> harus jalankan virtual_usb.py dulu
        self.lamp = LampController('/dev/ttyUSB0')

        self.buffer = ""

        self.stable_time = 5 # detik

        self.last_weight = None
        self.start_same_time = None
        self.is_stable = False
        self.last_frame_array = None

        self.pending_rfid = None
        self.already_sent = False

        self.lock = threading.Lock()  # 🔐 proteksi antar thread

        self.lamp.off()

    # =========================
    # STATUS HANDLER
    # =========================
    def handle_empty(self):
        with self.lock:
            # print("🟡 TIDAK ADA BEBAN")
            self.reset_state()

    def handle_unstable(self, weight):
        with self.lock:
            self.last_weight = weight
            self.start_same_time = time.time()
            self.is_stable = False
            self.already_sent = False
            self.lamp.off()

    def handle_stable(self):
        with self.lock:
            if not self.is_stable:
                print("🔥 TIMBANGAN STABIL")
                self.is_stable = True
                self.lamp.red_on()

            self.try_send()

    def reset_state(self):
        self.last_weight = None
        self.start_same_time = None
        self.is_stable = False
        self.pending_rfid = None
        self.already_sent = False
        self.lamp.off()

    # =========================
    # CENTRAL SEND CHECK
    # =========================
    def try_send(self):
        """
        Kirim hanya jika:
        - Stabil
        - Ada RFID
        - Belum pernah kirim
        """
        if self.is_stable and self.pending_rfid and not self.already_sent:
            self.already_sent = True
            self.send_to_server()

    # =========================
    # KIRIM DATA
    # =========================
    def send_to_server(self):
        self.lamp.blink_green()
        print("📡 Mengirim data ke server...")
        time.sleep(3)

        # url = "http://php8.local/murti/api.php"
        url = "http://172.27.27.91:8000/api/v1/timbang"

        payload = {
            "rfid": self.pending_rfid,
            "data": self.last_frame_array
        }

        result = None
        response = None
        try:
            response = requests.post(url, json=payload, timeout=5)
            # response = requests.post(url, data=payload, timeout=5)
            result = response.json()
            # print(payload)
            # print(result)
            if result["code"] == 201:
                print("✅ Sukses:", result["message"])
                self.lamp.green_on()
                time.sleep(10)
            elif result["code"] not in [201, 500]: # tidak boleh masuk
                 print(result["message"])
                 self.lamp.blink_red()
                 time.sleep(5)
            else:
                print("❌ HTTP error:", response.status_code, ": ", result["message"])
                self.lamp.blink_both()
                time.sleep(5)
        except Exception as e:
            print("❌ Error kirim:", e)
            self.lamp.blink_both()
            time.sleep(5)

        self.pending_rfid = None

    # =========================
    # FRAME PROCESSOR
    # =========================
    def process_frame(self, parts):
        if len(parts) != 3:
            return

        self.last_frame_array = parts.copy()
        part1, weight, part3 = parts

        # CEK KOSONG
        if weight == "000" and part3 == "00":
            self.handle_empty()
            return

        # CEK STABIL 5 DETIK
        if weight == self.last_weight:
            if self.start_same_time is None:
                self.start_same_time = time.time()

            if time.time() - self.start_same_time >= self.stable_time:
                self.handle_stable()
        else:
            self.handle_unstable(weight)

    # =========================
    # SERIAL LOOP
    # =========================
    def read_serial(self):
        while True:
            data = self.ser.read(1)

            if not data:
                continue

            byte = data[0]

            if byte == 2:  # STX
                self.buffer = ""
                continue

            elif byte == 13:  # CR
                if self.buffer:
                    parts = self.buffer.strip().split()
                    self.process_frame(parts)

                self.buffer = ""
                continue

            else:
                self.buffer += chr(byte)

    # =========================
    # RFID LISTENER (HID keyboard)
    # =========================
    def rfid_listener(self):
        while True:
            rfid = input("Tap RFID: \n").strip()

            if not rfid:
                continue

            with self.lock:
                if not self.is_stable:
                    print("🟡 Timbangan belum stabil, silahkan tunggu...")
                    continue

                print("📥 RFID diterima:", rfid)
                self.pending_rfid = rfid
                self.try_send()

    # =========================
    # START SYSTEM
    # =========================
    def start(self):
        threading.Thread(target=self.read_serial, daemon=True).start()
        threading.Thread(target=self.rfid_listener, daemon=True).start()
        threading.Event().wait()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        receiver = ScaleReceiver()
        receiver.start()
    except serial.SerialException as e:
        print("Serial error:", e)