import serial
import threading
import time


class LampController:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, blink_interval=0.5):
        self.ser = serial.Serial(port, baudrate, timeout=1)

        # Mode: off / on / blink
        self.red_mode = "off"
        self.green_mode = "off"

        self.blink_interval = blink_interval
        self.running = True

        self.lock = threading.Lock()

        # Start worker thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # ==================================
    # PUBLIC CONTROL METHOD
    # ==================================

    def set_mode(self, red="off", green="off"):
        """
        red / green:
        - "off"
        - "on"
        - "blink"
        """
        with self.lock:
            self.red_mode = red
            self.green_mode = green

    # Shortcut helpers (optional biar gampang dipanggil)
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

    def off(self):
        self.set_mode("off", "off")

    def red_on(self):
        self.set_mode("on", "off")

    def green_on(self):
        self.set_mode("off", "on")

    def yellow_on(self):
        self.set_mode("on", "on")

    def blink_red(self):
        self.set_mode("blink", "off")

    def blink_green(self):
        self.set_mode("on", "blink")

    def blink_both(self):
        self.set_mode("blink", "blink")

    def stop(self):
        self.running = False
        self.thread.join()

    # ==================================
    # INTERNAL THREAD
    # ==================================

    def _run(self):
        blink_state = False

        while self.running:
            with self.lock:
                red_mode = self.red_mode
                green_mode = self.green_mode

            blink_state = not blink_state

            # Red logic
            if red_mode == "on":
                red = 1
            elif red_mode == "off":
                red = 0
            elif red_mode == "blink":
                red = 1 if blink_state else 0
            else:
                red = 0

            # Green logic
            if green_mode == "on":
                green = 1
            elif green_mode == "off":
                green = 0
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
        cmd = f"{red}{green}\n"
        try:
            self.ser.write(cmd.encode())
        except Exception as e:
            print("Lamp serial error:", e)