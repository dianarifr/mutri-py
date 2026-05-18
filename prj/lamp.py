import serial
import threading
import time


# ==================================
# SHORTCUT HELPER
# ==================================
"""
# R0 G0
lamp.off()

# R1 G0
lamp.red_on()

# R1 G1/2
lamp.blink_green()

# R1/2 G1/2
lamp.blink_both()

# R1/2 G0
lamp.blink_red()

# R1 G1
lamp.yellow_on()
"""


class LampController:

    def __init__(
        self,
        port='/tmp/usb_virtual_rx',
        baudrate=115200,
        blink_interval=0.5
    ):

        self.port = port
        self.baudrate = baudrate

        self.ser = None
        self.connected = False

        self.red_mode = "off"
        self.green_mode = "off"

        self.blink_interval = blink_interval
        self.running = True

        self.lock = threading.Lock()
        self.mode_until = None
        self.default_mode = ("off", "off")

        # anti spam log
        self.last_wait_print = 0

        # =========================
        # START THREAD
        # =========================

        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )

        self.reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True
        )

        self.health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )

        self.worker_thread.start()
        self.reconnect_thread.start()
        self.health_thread.start()

    # ==================================
    # RECONNECT LOOP
    # ==================================

    def _reconnect_loop(self):

        while self.running:

            if not self.connected:

                try:
                    self.ser = serial.Serial(
                        self.port,
                        self.baudrate,
                        timeout=1
                    )

                    self.connected = True

                    print(f"✅ Lampu terhubung: {self.port}")

                except Exception:

                    now = time.time()

                    # biar ga spam terminal
                    if now - self.last_wait_print >= 5:
                        print(f"🟡 Menunggu lampu terhubung: {self.port}")
                        self.last_wait_print = now

            time.sleep(2)

    # ==================================
    # HEALTH CHECK
    # ==================================

    def _health_check_loop(self):

        while self.running:

            if self.connected and self.ser:

                try:
                    # heartbeat kecil
                    self.ser.write(b'')

                except Exception as e:

                    print("🟡 Health check failed:", e)

                    self._disconnect()

            time.sleep(3)

    # ==================================
    # DISCONNECT HANDLER
    # ==================================

    def _disconnect(self):

        self.connected = False

        if self.ser:
            try:
                self.ser.close()
            except:
                pass

        self.ser = None

    # ==================================
    # PUBLIC CONTROL
    # ==================================

    def set_mode(self, red="off", green="off", duration=None):

        with self.lock:

            self.red_mode = red
            self.green_mode = green

            if duration:
                self.mode_until = time.time() + duration
            else:
                self.mode_until = None

    def off(self, duration=None):
        self.set_mode("off", "off", duration)

    def red_on(self, duration=None):
        self.set_mode("on", "off", duration)

    def green_on(self, duration=None):
        self.set_mode("off", "on", duration)

    def yellow_on(self, duration=None):
        self.set_mode("on", "on", duration)

    def blink_red(self, duration=None):
        self.set_mode("blink", "off", duration)

    def blink_green(self, duration=None):
        self.set_mode("on", "blink", duration)

    def blink_both(self, duration=None):
        self.set_mode("blink", "blink", duration)

    # ==================================
    # WORKER LOOP
    # ==================================

    def _worker_loop(self):

        blink_state = False

        while self.running:

            with self.lock:
                # auto reset duration
                if (
                    self.mode_until
                    and time.time() >= self.mode_until
                ):

                    self.red_mode, self.green_mode = self.default_mode

                    self.mode_until = None

                red_mode = self.red_mode
                green_mode = self.green_mode

            blink_state = not blink_state

            # =========================
            # RED
            # =========================

            if red_mode == "on":
                red = 1
            elif red_mode == "blink":
                red = 1 if blink_state else 0
            else:
                red = 0

            # =========================
            # GREEN
            # =========================

            if green_mode == "on":
                green = 1
            elif green_mode == "blink":
                green = 1 if blink_state else 0
            else:
                green = 0

            self._write(red, green)

            time.sleep(self.blink_interval)

    # ==================================
    # SERIAL WRITE
    # ==================================

    def _write(self, red, green):

        if not self.connected or not self.ser:
            return

        cmd = f"{red}{green}\n"

        try:
            self.ser.write(cmd.encode())

        except Exception as e:

            print("🟡 Lampu terputus:", e)

            self._disconnect()

    # ==================================
    # STOP
    # ==================================

    def stop(self):

        self.running = False

        self._disconnect()

        self.worker_thread.join()
        self.reconnect_thread.join()
        self.health_thread.join()