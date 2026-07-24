# receiver_scale.py

from logger import print

import serial
import time
import threading
import requests
import configparser
import queue
import socket

from urllib.parse import urlparse
from lamp import LampController


# =========================
# CONFIG
# =========================

config = configparser.ConfigParser()
config.read('config.ini')

scale_port = config['prj']['usb_scale_port']
lamp_port = config['prj']['usb_lamp_port']

default_stable_time = int(config['prj']['stable_time'])

api_url = config['prj']['api_url']
api_key = config['prj']['api_key']
stable_weight_tolerance = config['prj']['stable_weight_tolerance']

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

        self.tolerance = int(stable_weight_tolerance)
        self.api_url = api_url
        self.api_key = api_key

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

        self.weight_history = []
        self.last_weight = None
        # self.start_same_time = None

        self.is_stable = False

        self.last_frame_array = None

        self.pending_rfid = None
        self.already_sent = False
        self.last_empty_log = 0
        self.intentional_disconnect = False

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
                    self.intentional_disconnect = False
                    self.last_data_time = time.time()

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
        self.intentional_disconnect = True
        self.connected = False

        if self.ser:
            try:
                self.ser.close()
            except:
                pass
        self.ser = None

    # ==================================
    # INTERNET CHECK
    # ==================================

    def _is_internet_ok(self):
        try:
            # Mencoba koneksi ke Google DNS port 53 dengan timeout 2 detik
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    # ==================================
    # API HOST CHECK
    # ==================================

    def _is_api_host_reachable(self):
        try:
            # Memecah URL untuk mengambil nama domain/IP dan port-nya
            parsed_url = urlparse(self.api_url)
            hostname = parsed_url.hostname

            # Tentukan port default berdasarkan http atau https
            port = parsed_url.port if parsed_url.port else (443 if parsed_url.scheme == "https" else 80)

            # Mencoba koneksi socket ke server API
            socket.create_connection((hostname, port), timeout=2)
            return True
        except OSError:
            return False

    # ==================================
    # WATCHDOG
    # ==================================

    def watchdog_loop(self):
        while True:
            if self.connected:
                timeout = time.time() - self.last_data_time

                # 5 detik tidak ada data
                if timeout >= 5:
                    print("🟡 Timbangan tidak ada response...")
                    self.disconnect_serial()
            time.sleep(2)

    # =========================
    # STATUS HANDLER
    # =========================

    def handle_empty(self):
        should_reset = False

        with self.lock:
            now = time.time()
            # tampilkan max 1x tiap 5 detik
            if now - self.last_empty_log >= 5:
                print("🟡 Timbangan tidak ada beban...")
                self.last_empty_log = now

            if self.is_stable or self.already_sent:
                should_reset = True

        if should_reset:
            self.reset_state()

    def handle_unstable(self, weight):
        should_trigger_lamp_off = False

        with self.lock:
            # self.start_same_time = time.time()
            self.last_weight = weight

            if self.is_stable or self.already_sent:
                self.is_stable = False
                self.already_sent = False
                should_trigger_lamp_off = True

        if should_trigger_lamp_off:
            self.lamp.off()

    def handle_stable(self):
        should_trigger_lamp = False

        with self.lock:
            if not self.is_stable:
                should_trigger_lamp = True
                part1, weight, part3 = self.last_frame_array
                print(f"🔥 Timbangan stabil: {weight}")
                self.is_stable = True
            self.try_send()

        if should_trigger_lamp:
            self.lamp.red_on()

    def reset_state(self):
        with self.lock:
            self.last_weight = None
            self.is_stable = False
            self.pending_rfid = None
            self.already_sent = False
            # self.start_same_time = None
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
                "data": self.last_frame_array,
                "api_key": self.api_key,
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
        print("🔍 Memeriksa kestabilan internet...")
        if not self._is_internet_ok():
            print("❌ Internet tidak stabil / terputus!")
            self.lamp.blink_both(duration=3)
            return
        else:
            print("✅ Internet stabil")

        print("🔍 Memeriksa koneksi ke server API...")
        if not self._is_api_host_reachable():
            print("❌ Server API down / tidak dapat dijangkau (Ping Fail)!")
            self.lamp.blink_both(duration=3)
            return
        else:
            print("✅ Server API dapat dijangkau")

        self.lamp.blink_green(duration=3)
        print("📡 Mengirim data ke server...")

        log_payload = payload.copy()
        if "api_key" in log_payload:
            log_payload["api_key"] = "********"

        print(f"📦 Data Payload: {log_payload}")

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=15
            )

            # validasi json
            try:
                result = response.json()
            except Exception:
                print("❌ Response bukan JSON")
                print(f"ℹ️ HTTP Status Code: {response.status_code}")
                print(f"📄 Response server: {response.text[:500]}")
                self.lamp.blink_both(duration=5)
                return

            if result.get("code") == 201:
                print("✅ Sukses:", result.get("message", "No message"))
                self.lamp.green_on(duration=10)
            elif result.get("code") not in [201, 500]:
                print("🟡", result.get("message", "Warning/Custom Error"))
                self.lamp.blink_red(duration=5)
            else:
                print(
                    "❌ HTTP error:",
                    response.status_code,
                    ":",
                    result.get("message", "Internal Server Error")
                )
                self.lamp.blink_both(duration=5)
        except Exception as e:
            print("❌ Error kirim:", e)
            self.lamp.blink_both(duration=5)
        finally:
            with self.lock:
                self.pending_rfid = None

    # =========================
    # FRAME PROCESSOR
    # =========================

    def process_frame(self, parts):
        if not parts or len(parts) != 3:
            return

        with self.lock:
            self.last_frame_array = parts.copy()

        part1, weight, part3 = parts

        if (weight == "000" or weight == "00") and part3 == "00":
            self.handle_empty()
            return

        # =========================
        # STABLE CHECK
        # =========================

        try:
            current_val = int(weight)
        except ValueError:
            return # Abaikan jika data corrupt ("ERR", "OVER", dll)

        now = time.time()
        is_stable_now = False

        with self.lock:
            # Catat waktu dan nilai berat saat ini ke dalam riwayat
            self.weight_history.append((now, current_val))

            # Buang data riwayat yang usianya melebihi stable_time (+ 0.5 detik untuk buffer memori)
            valid_window = self.stable_time + 0.5
            self.weight_history = [
                (t, w) for t, w in self.weight_history
                if (now - t) <= valid_window
            ]

            # Evaluasi Stabilitas (syarat: minimal ada 2 data di riwayat)
            if len(self.weight_history) > 1:
                # Ambil waktu dari data paling lama di riwayat
                first_time = self.weight_history[0][0]

                # Cek apakah durasi riwayat sudah memenuhi batas waktu stable_time
                if (now - first_time) >= self.stable_time:
                    # Ekstrak angkanya saja dari list history
                    weights = [w for t, w in self.weight_history]

                    # Cari selisih nilai Tertinggi dan Terendah
                    fluctuation = max(weights) - min(weights)

                    # Jika fluktuasinya masuk dalam batas toleransi (misal <= 10)
                    if fluctuation <= self.tolerance:
                        is_stable_now = True

        if is_stable_now:
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
                ser = self.ser

                if not ser:
                    time.sleep(1)
                    continue

                data = ser.read(1)

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
                if not self.intentional_disconnect:
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
                    print("🟡 Timbangan belum stabil, silahkan tunggu...")
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