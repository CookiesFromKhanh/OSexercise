"""controller.py - Home Controller (start this FIRST, in terminal 1).
Creates the shared memory, polls the flag, forks one child per event."""
import os
import time
from multiprocessing import shared_memory

from common import *

TAG = "CONTROL"


# ---- device functions: run inside the child, print only ----
def Light(d):       print(f"Brightness set to {d}%", flush=True)
def Motion(d):      print(f"Motion {d}", flush=True)
def Door(d):        print(f"Door is {d}", flush=True)
def Temperature(d): print(f"Thermostat set to {d}", flush=True)

DEVICES = {"light": Light, "motion": Motion, "door": Door, "temperature": Temperature}


def child_run(event, data):
    """Runs in the forked child. Never returns."""
    print(f"[CHILD  ] PID={os.getpid()} PPID={os.getppid()} event={event} data={data} -> ",
          end="", flush=True)
    DEVICES[event](data)
    log("CHILD  ", f"PID={os.getpid()} exiting")
    os._exit(0)          # _exit: skip the parent's cleanup/atexit code in the child


children = set()          # PIDs of the device children WE forked


def reap_finished():
    """non-blocking: collect finished children so no zombies pile up"""
    for pid in list(children):
        done, _ = os.waitpid(pid, os.WNOHANG)
        if done:
            children.discard(pid)
            log(TAG, f"child PID={pid} finished")


def main():
    log(TAG, f"Home Controller started, PID={os.getpid()}")

    # remove a stale segment left behind by a crashed earlier run
    try:
        old = shared_memory.SharedMemory(name=SHM_NAME)
        old.close()
        old.unlink()
    except FileNotFoundError:
        pass

    shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
    buf = shm.buf
    buf[:SHM_SIZE] = bytes(SHM_SIZE)
    buf[FLAG_OFF] = FLAG_EMPTY
    log(TAG, f"shared memory created (name={SHM_NAME}, {SHM_SIZE} bytes), flag=0")
    log(TAG, "waiting for events...")

    try:
        while True:
            if buf[FLAG_OFF] == FLAG_FULL:
                event = get_text(buf, EVENT_OFF, EVENT_LEN)
                data = get_text(buf, DATA_OFF, DATA_LEN)
                log(TAG, f"flag=1 -> READ  event={event} data={data}")

                buf[FLAG_OFF] = FLAG_EMPTY                 # free the handler
                log(TAG, "flag set 1 -> 0")

                if event == "exit":
                    log(TAG, "handler is shutting down")
                    break

                pid = os.fork()
                if pid == 0:
                    child_run(event, data)
                children.add(pid)
                log(TAG, f"forked child PID={pid} for '{event}'")
            else:
                reap_finished()
                time.sleep(POLL_S)
    except KeyboardInterrupt:
        log(TAG, "interrupted (Ctrl+C)")
    finally:
        log(TAG, "waiting for all children...")
        # wait for OUR children only: os.wait() would also block on Python's own
        # helper process (the shared-memory resource tracker) which lives until we exit
        for pid in list(children):
            os.waitpid(pid, 0)
            children.discard(pid)
            log(TAG, f"child PID={pid} finished")

        buf = None                       # drop our view before closing
        shm.close()
        log(TAG, "detached from shared memory")
        shm.unlink()
        log(TAG, "shared memory segment removed")
        log(TAG, "bye")


if __name__ == "__main__":
    main()
