# receiver_scale.py

import serial
import time
import threading
import requests
import configparser
import queue

from lamp import LampController


# =========================
# CONFIG
# =========================

config = configparser.ConfigParser()
config.read('config.ini')

scale_port = config['prj']['usb_scale_port']
lamp_port = config['prj']['usb_lamp_port']

default_stable_time = int(config['prj']['stable_time'])

url_api = config['prj']['url_api']
key_api = config['prj']['key_api']


class ScaleReceiver:

    def __init__(self, port=scale_port, baudrate=9600):

        # =========================
        # SERIAL SCALE
        # =========================

        self.port = port
        self.baudrate = baudrate

        self.ser = None
        self.connected = False

        self.last_wait_print = 0
        self.last_data_time = time.time()

        # =========================
        # LAMP
        # =========================

        self.lamp = LampController(lamp_port)

        # =========================
        # BUFFER
        # =========================

        self.buffer = ""

        # =========================
        # STABLE CONFIG
        # =========================

        self.stable_time = default_stable_time

        # =========================
        # STATE
        # =========================

        self.last_weight = None
        self.start_same_time = None

        self.is_stable = False

        self.last_frame_array = None

        self.pending_rfid = None
        self.already_sent = False
        self.last_empty_log = 0

        # =========================
        # THREAD SAFE
        # =========================

        self.lock = threading.Lock()

        # =========================
        # API QUEUE
        # =========================

        self.api_queue = queue.Queue()

        # =========================
        # DEFAULT LAMP
        # =========================

        self.lamp.off()

    # ==================================
    # SERIAL CONNECT
    # ==================================

    def serial_reconnect_loop(self):

        while True:

            if not self.connected:

                try:

                    self.ser = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        timeout=1
                    )

                    self.connected = True

                    print(f"✅ Timbangan terhubung: {self.port}")

                except Exception:

                    now = time.time()

                    if now - self.last_wait_print >= 5:
                        print(f"🟡 Menunggu timbangan terhubung: {self.port}")
                        self.last_wait_print = now

            time.sleep(2)

    # ==================================
    # SERIAL DISCONNECT
    # ==================================

    def disconnect_serial(self):

        self.connected = False

        if self.ser:
            try:
                self.ser.close()
            except:
                pass

        self.ser = None

    # ==================================
    # WATCHDOG
    # ==================================

    def watchdog_loop(self):

        while True:

            if self.connected:

                timeout = time.time() - self.last_data_time

                # 10 detik tidak ada data
                if timeout >= 10:

                    print("🟡 Timbangan timeout...")

                    self.disconnect_serial()

            time.sleep(2)

    # =========================
    # STATUS HANDLER
    # =========================

    def handle_empty(self):

        with self.lock:

            now = time.time()

            # tampilkan max 1x tiap 5 detik
            if now - self.last_empty_log >= 5:

                print("🟡 Timbangan tidak ada beban...")

                self.last_empty_log = now

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

                part1, weight, part3 = self.last_frame_array

                print(f"🔥 Timbangan stabil: {weight}")

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

        if (
            self.is_stable
            and self.pending_rfid
            and not self.already_sent
        ):

            self.already_sent = True

            payload = {
                "rfid": self.pending_rfid,
                "data": self.last_frame_array
            }

            self.api_queue.put(payload)

    # =========================
    # API WORKER
    # =========================

    def api_worker_loop(self):

        while True:

            payload = self.api_queue.get()

            self.send_to_server(payload)

            self.api_queue.task_done()

    # =========================
    # SEND API
    # =========================

    def send_to_server(self, payload):

        self.lamp.blink_green(duration=3)

        print("📡 Mengirim data ke server...")

        try:

            response = requests.post(
                url_api,
                json=payload,
                timeout=5
            )

            # validasi json
            try:
                result = response.json()

            except Exception:

                print("❌ Response bukan JSON")

                self.lamp.blink_both(duration=5)

                return

            # =========================
            # SUCCESS
            # =========================

            if result["code"] == 201:

                print("✅ Sukses:", result["message"])

                self.lamp.green_on(duration=10)

            # =========================
            # CUSTOM ERROR
            # =========================

            elif result["code"] not in [201, 500]:

                print("🟡", result["message"])

                self.lamp.blink_red(duration=5)

            # =========================
            # SERVER ERROR
            # =========================

            else:

                print(
                    "❌ HTTP error:",
                    response.status_code,
                    ":",
                    result["message"]
                )

                self.lamp.blink_both(duration=5)

        except Exception as e:

            print("❌ Error kirim:", e)

            self.lamp.blink_both(duration=5)

        finally:

            self.pending_rfid = None

    # =========================
    # FRAME PROCESSOR
    # =========================

    def process_frame(self, parts):

        if len(parts) != 3:
            return

        self.last_frame_array = parts.copy()

        part1, weight, part3 = parts

        # =========================
        # EMPTY
        # =========================

        if (weight == "000" or weight == "00") and part3 == "00":

            self.handle_empty()

            return

        # =========================
        # STABLE CHECK
        # =========================

        if weight == self.last_weight:

            if self.start_same_time is None:
                self.start_same_time = time.time()

            if (
                time.time() - self.start_same_time
                >= self.stable_time
            ):

                self.handle_stable()

        else:

            self.handle_unstable(weight)

    # =========================
    # SERIAL LOOP
    # =========================

    def read_serial(self):

        while True:

            # belum connect
            if not self.connected or not self.ser:

                time.sleep(1)

                continue

            try:

                data = self.ser.read(1)

                if not data:
                    continue

                # watchdog timestamp
                self.last_data_time = time.time()

                byte = data[0]

                # STX
                if byte == 2:

                    self.buffer = ""

                    continue

                # CR
                elif byte == 13:

                    if self.buffer:

                        parts = self.buffer.strip().split()

                        self.process_frame(parts)

                    self.buffer = ""

                    continue

                else:

                    self.buffer += chr(byte)

            except Exception as e:

                print("🟡 Timbangan terputus:", e)

                self.disconnect_serial()

                time.sleep(1)

    # =========================
    # RFID LISTENER
    # =========================

    def rfid_listener(self):

        while True:

            rfid = input("Tap RFID:\n").strip()

            if not rfid:
                continue

            with self.lock:

                if not self.is_stable:

                    print(
                        "🟡 Timbangan belum stabil, silahkan tunggu..."
                    )

                    continue

                print("📥 RFID diterima:", rfid)

                self.pending_rfid = rfid

                self.try_send()

    # =========================
    # START SYSTEM
    # =========================

    def start(self):

        threading.Thread(
            target=self.serial_reconnect_loop,
            daemon=True
        ).start()

        threading.Thread(
            target=self.watchdog_loop,
            daemon=True
        ).start()

        threading.Thread(
            target=self.read_serial,
            daemon=True
        ).start()

        threading.Thread(
            target=self.rfid_listener,
            daemon=True
        ).start()

        threading.Thread(
            target=self.api_worker_loop,
            daemon=True
        ).start()

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