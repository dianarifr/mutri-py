import subprocess
import time
import os
import sys
import signal

# ==============================
# KONFIGURASI VIRTUAL USB
# ==============================

USB_TX = "/tmp/usb_virtual_tx"
USB_RX = "/tmp/usb_virtual_rx"

SOCAT_CMD = [
    "socat",
    "-d",
    "-d",
    f"pty,raw,echo=0,link={USB_TX}",
    f"pty,raw,echo=0,link={USB_RX}",
]

# ==============================
# HELPER
# ==============================

def remove_old_virtual():
    for path in [USB_TX, USB_RX]:
        if os.path.exists(path):
            os.remove(path)

def start_socat():
    print("Starting SAFE virtual USB...")
    return subprocess.Popen(
        SOCAT_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

def graceful_exit(process):
    print("\nStopping virtual USB safely...")
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
    sys.exit(0)

# ==============================
# MAIN LOOP
# ==============================

def main():
    process = None

    while True:
        try:
            remove_old_virtual()

            process = start_socat()

            # Tunggu sampai file device muncul
            for _ in range(10):
                if os.path.exists(USB_RX):
                    break
                time.sleep(0.5)

            print(f"Virtual USB ready:")
            print(f"  WRITE  -> {USB_TX}")
            print(f"  READ   -> {USB_RX}")
            print("")

            process.wait()

            print("Socat stopped. Restarting in 2 seconds...\n")
            time.sleep(2)

        except KeyboardInterrupt:
            graceful_exit(process)

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()