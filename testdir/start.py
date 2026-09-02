# coding:utf-8
# write by zkp
import os
import sys
import time



if __name__ == '__main__':
    os.system("cd /data/code/happytime-rtsp-server && sh start.sh")
    os.system("cd /data/code/happytime-rtmp-server && sh start.sh")
    while 1:
        time.sleep(1)

