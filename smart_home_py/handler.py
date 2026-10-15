"""handler.py - Sensor Event Handler (start SECOND, in terminal 2).
Reads user input, validates it, writes valid events to shared memory."""
import os
import re
import time
from multiprocessing import shared_memory, resource_tracker

from common import *

TAG = "HANDLER"
INT_RE = re.compile(r"[0-9]+")       # ASCII digits only


def validate(line):
    """returns (event, data, None) if valid, or (None, None, error_message)"""
    tok = line.lower().split()
    if not tok:
        return None, None, "empty input"
    if len(tok) == 1:
        return None, None, "missing value (format: <event> <value>)"
    if len(tok) > 2:
        return None, None, "too many words (format: <event> <value>)"
    event, data = tok

    if event == "light":
        if not (INT_RE.fullmatch(data) and 0 <= int(data) <= 100):
            return None, None, "light needs an integer 0-100"
    elif event == "motion":
        if data not in ("detected", "clear"):
            return None, None, "motion needs 'detected' or 'clear'"
    elif event == "door":
        if data not in ("open", "closed"):
            return None, None, "door needs 'open' or 'closed'"
    elif event == "temperature":
        if not (INT_RE.fullmatch(data) and 15 <= int(data) <= 30):
            return None, None, "temperature needs an integer 15-30"
    else:
        return None, None, "unknown event (valid: light, motion, door, temperature)"
    return event, data, None


def attach():
    """attach to the segment the controller created (never create it here)"""
    try:
        return shared_memory.SharedMemory(name=SHM_NAME, track=False)   # Python 3.13+
    except TypeError:
        shm = shared_memory.SharedMemory(name=SHM_NAME)
        # older Pythons make this process 'own' the segment and would delete it
        # on exit; the controller is the owner, so tell the tracker to stay out
        resource_tracker.unregister(shm._name, "shared_memory")
        return shm


def send_event(buf, event, data):
    """wait until flag==0, write event+data, then set flag=1"""
    announced = False
    while buf[FLAG_OFF] != FLAG_EMPTY:
        if not announced:
            log(TAG, "flag=1, waiting for controller to read...")
            announced = True
        time.sleep(POLL_S)
    put_text(buf, EVENT_OFF, EVENT_LEN, event)
    put_text(buf, DATA_OFF, DATA_LEN, data)
    log(TAG, f"WROTE event={event} data={data} to shared memory")
    buf[FLAG_OFF] = FLAG_FULL            # flag LAST: data is complete before it flips
    log(TAG, "flag set 0 -> 1")


def main():
    log(TAG, f"Sensor Event Handler started, PID={os.getpid()}")
    try:
        shm = attach()
    except FileNotFoundError:
        log(TAG, "cannot find shared memory - start the controller first")
        return 1
    buf = shm.buf
    log(TAG, f"attached to shared memory (name={SHM_NAME})")
    log(TAG, "events: light 0-100 | motion detected/clear | door open/closed | "
             "temperature 15-30 | exit")

    try:
        while True:
            try:
                line = input("> ")
            except EOFError:             # Ctrl+D behaves like 'exit'
                line = "exit"

            if line.strip().lower() == "exit":
                send_event(buf, "exit", "-")      # tell the controller we are leaving
                break

            event, data, err = validate(line)
            if err:
                log(TAG, f"INVALID: {err}. Try again.")   # never reaches shared memory
                continue
            send_event(buf, event, data)
    except KeyboardInterrupt:
        print()
    finally:
        buf = None
        shm.close()
        log(TAG, "detached from shared memory, exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
