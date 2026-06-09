import os
import datetime
import builtins
import logging
from logging.handlers import TimedRotatingFileHandler

# ====================================================
# 1. OTOMATISASI FOLDER LOG & PERMISSION (0o777)
# ====================================================
log_dir = "log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir, mode=0o777, exist_ok=True)
else:
    try:
        os.chmod(log_dir, 0o777)
    except Exception:
        pass

# ====================================================
# 2. CONFIGURATION LOGGING SYSTEM
# ====================================================
logger = logging.getLogger("ScaleLogger")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# HANDLER 1: Terminal (Console)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# HANDLER 2: File (.log) otomatis ganti tiap tengah malam
log_file_path = os.path.join(log_dir, "timbangan.log")
file_handler = TimedRotatingFileHandler(
    log_file_path,
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
file_handler.suffix = "%Y-%m-%d.log"
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# ====================================================
# 3. FUNGSI PEMBAJAK PRINT GLOBAL
# ====================================================
def print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    logger.info(message)