# 兼容python 3.8  3.9  3.10  3.11  3.12
FROM python:3.12.11
MAINTAINER zhoukunpeng<zhoukunpeng504@163.com>
RUN apt-get update
RUN apt install -y vim htop gcc g++ pkg-config lrzsz
RUN mkdir -p /data/logs
COPY .  /data/code
WORKDIR /data/code
# pip源设置
RUN rm -rf ~/.pip && mkdir ~/.pip
RUN cd /data/code && pip3 install -r requirements.txt
#RUN mkdir -p /data/rtsp_py
# REDIS地址，如有密码把密码按格式组装到REDIS_URL  中
ENV REDIS_URL redis://127.0.0.1:6379/8
# ENV NACOS_REGISTER_IP ''
ENV PYTHONUNBUFFERED 1
EXPOSE 8005
EXPOSE 8006
WORKDIR /data/code
ENTRYPOINT ["python3", "server.py"]
