FROM ubuntu:24.04
MAINTAINER zhoukunpeng<zhoukunpeng504@163.com>
RUN apt-get update
RUN apt install -y vim htop gcc g++ pkg-config lrzsz redis nload python3 python3-pip python3-psutil python3-requests unzip libasound2-dev
RUN mkdir -p /data/logs
COPY ./testdir  /data/code
WORKDIR /data/code
# pip源设置
RUN ls -al /data/code
RUN cd /data/code/ && unzip -o happytime-rtmp-server.zip && unzip -o happytime-rtsp-server.zip
#
ENV PYTHONUNBUFFERED=1
# RTSP PORT
EXPOSE 554
# RTMP PORT
EXPOSE 1935
WORKDIR /data/code
ENTRYPOINT ["python3", "start.py"]