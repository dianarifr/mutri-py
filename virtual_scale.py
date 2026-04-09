import subprocess
import time
import os
import signal

SOCAT_CMD = [
    "socat",
    "-d",
    "-d",
    "pty,raw,echo=0,link=/tmp/scale_tx",
    "pty,raw,echo=0,link=/tmp/scale_rx",
]

def remove_old_links():
    for path in ["/tmp/scale_tx", "/tmp/scale_rx"]:
        if os.path.exists(path):
            os.remove(path)

def start_socat():
    print("Starting virtual serial...")
    return subprocess.Popen(SOCAT_CMD)

def main():
    while True:
        try:
            remove_old_links()
            process = start_socat()

            # Tunggu sampai socat berhenti
            process.wait()

            print("Socat stopped! Restarting in 2 seconds...\n")
            time.sleep(2)

        except KeyboardInterrupt:
            print("\nStopping virtual serial...")
            process.terminate()
            break

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()