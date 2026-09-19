FROM ubuntu:24.04
MAINTAINER zhoukunpeng<zhoukunpeng504@163.com>
RUN apt-get update
RUN apt install -y vim htop gcc g++ wget pkg-config lrzsz redis nload python3 python3-pip python3-psutil python3-requests unzip libasound2-dev
RUN mkdir -p /data/logs
COPY ./testdir  /data/code
WORKDIR /data/code
# pip源设置
RUN ls -al /data/code
RUN cd /data/code/ && unzip -o happytime-rtmp-server.zip && unzip -o happytime-rtsp-server.zip && \
    cd /data/code/ && wget http://starchain.cn.gcimg.net/007/generated_videos.zip  && unzip  generated_videos.zip && \
    cd /data/code/ && rm -rf  /data/code/happytime-rtsp-server/*.mp4  && cp -a /data/code/generated_videos/*.mkv /data/code/happytime-rtsp-server && \
    cd /data/code/ && rm -rf  /data/code/happytime-rtmp-server/*.mp4  && cp -a /data/code/generated_videos/*.mkv /data/code/happytime-rtmp-server && \
    rm -rf /data/code/generated_videos
#
ENV PYTHONUNBUFFERED=1
# RTSP PORT
EXPOSE 554
# RTMP PORT
EXPOSE 1935
WORKDIR /data/code
ENTRYPOINT ["python3", "start.py"]