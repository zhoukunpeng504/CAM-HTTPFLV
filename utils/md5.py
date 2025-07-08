# coding:utf-8
__author__ = "zkp"
# create by zkp on 2022/2/8
import hashlib


def md5(_s:str):
    a = hashlib.md5(_s.encode()).hexdigest()
    return a

def md5_int(_str: str):
    _ = hashlib.md5(_str.encode('utf-8')).hexdigest()
    return int(_, 16)

if __name__ == '__main__':
    aa = md5("ss")
    print([aa])