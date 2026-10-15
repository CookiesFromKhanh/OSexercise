"""common.py - layout of the shared-memory segment used by both processes.

  offset  size  field   meaning
  ------  ----  -----   ----------------------------------------------
   0       4    flag    0 = empty (handler may write), 1 = event waiting
                        (only byte 0 is used; a 1-byte read/write is atomic)
   4      16    event   "light" | "motion" | "door" | "temperature" | "exit"
  20      16    data    value as text, e.g. "70", "detected", "open", "22"
  total   36 bytes

The segment holds raw bytes, so text is converted with encode()/decode().
"""
SHM_NAME   = "smart_home_shm"
FLAG_OFF   = 0
EVENT_OFF  = 4
DATA_OFF   = 20
EVENT_LEN  = 16
DATA_LEN   = 16
SHM_SIZE   = 36
FLAG_EMPTY = 0
FLAG_FULL  = 1
POLL_S     = 0.1          # polling interval: 100 ms


def log(tag, msg):
    print(f"[{tag}] {msg}", flush=True)


def put_text(buf, off, length, text):
    """write text into a fixed-size field, padded with zero bytes"""
    raw = text.encode()[:length - 1]
    buf[off:off + length] = raw.ljust(length, b"\0")


def get_text(buf, off, length):
    """read a fixed-size field back into a str"""
    return bytes(buf[off:off + length]).split(b"\0")[0].decode()
