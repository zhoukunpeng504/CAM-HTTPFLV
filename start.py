# coding:utf-8
# write by zkp
import psutil
import os
import sys
import time
import setproctitle
import threading


def clean_t():
    while True:
        for p_obj in psutil.Process(pid=1).children(recursive=False):
            try:
                if p_obj.status() == 'zombie':
                    p_obj.send_signal(9)
                    p_obj.kill()
                    p_obj.wait()
            except Exception as e:
                print("clean_t error", e)
        time.sleep(0.01)
        sys.stdout.flush()
        sys.stderr.flush()

def redis_run():
    while True:
        os.system("redis-server redis-6379.conf")


def httpflv_fun():
    while True:
        os.system("python3 server.py")


if __name__ == '__main__':
    setproctitle.setproctitle('main')
    thread = threading.Thread(target=clean_t, args=(), daemon=True)
    # thread.daemon = True
    thread.start()

    thread_2 = threading.Thread(target=redis_run, args=(), daemon=True)
    # thread_2.daemon = True
    thread_2.start()

    time.sleep(1.5)
    thread_1 = threading.Thread(target=httpflv_fun, args=(), daemon=True)
    # thread_1.daemon = True
    thread_1.start()



    while True:
        time.sleep(1)

