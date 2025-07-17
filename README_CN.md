# CAM-HTTPFLV
![License](https://img.shields.io/badge/license-GPLv3.0-blue)
![License](https://img.shields.io/badge/python-3.9-blue)
![License](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/python-3.12-blue)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/zhoukunpeng504/CAM-HTTPFLV/build.yml)
![Flask](https://img.shields.io/badge/Flask-000.svg?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)


CAM-HTTPFLV 支持两大核心功能：
- 把各种格式的RTSP、RTMP视频流转化为HTTPFLV格式的直播视频流(可支持在各种浏览器中访问)
- 对各种格式的RTSP、RTMP视频流进行在线快照，返回jpg格式的图像

在这里，我们简要介绍下CAM-HTTPFLV的支持的视频格式、主要功能以及如何使用。
## 内容
- CAM-HTTPFLV
  - 介绍
  - 我们为什么创造它
  - 支持的视频格式
  - 如何安装
    - 使用docker一键安装(推荐)
    - 使用源码安装
  - 视频源转HTTPFLV测试
    - RTSP转HTTPFLV
      - 启动RTSP测试视频源
      - 测试RTSP转HTTPFLV
    - RTMP转HTTPFLV
      - 启动RTMP测试视频源
      - 测试RTMP转HTTPFLV
    - 视频源实时快照
      - RTSP实时快照
      - RTMP实时快照

## 介绍
在视频结构化、智能安防、智慧城市等项目中需要频繁对摄像机进行在线访问，
然而摄像机内置的RTSP、RTMP视频流均无法直接在浏览器中访问。
目前，在中国基于HTTPFLV协议的视频直播正在各大平台广泛使用。(如：抖音直播、快手直播、斗鱼直播等)
为了解决现有RTSP、RTMP协议在web浏览器中难以访问的困境，并保持HTTPFLV协议的兼容，
我们开发了CAM-HTTPFLV项目。

## 支持的视频格式
如下格式已经经过兼容性测试。


| 视频源格式 | 视频编码 | 分辨率           | 音频编码 | 输出格式 | 输出视频编码 | 输出音频编码 |
| ---------- | -------- | ---------------- | -------- | -------- | ------------ | ------------ |
| RTSP       | h264     | 720p/1080p/2k/4k | G711A    | HTTP-FLV | h264         | AAC          |
| RTSP       | h264     | 720p/1080p/2k/4k | AAC      | HTTP-FLV | h264         | AAC          |
| RTSP       | h264     | 720p/1080p/2k/4k | G711U    | HTTP-FLV | h264         | AAC          |
| RTSP       | h264     | 720p/1080p/2k/4k | G722     | HTTP-FLV | h264         | AAC          |
| RTSP       | h264     | 720p/1080p/2k/4k | G726     | HTTP-FLV | h264         | AAC          |
| RTSP       | h264     | 720p/1080p/2k/4k | OPUS     | HTTP-FLV | h264         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | G711A    | HTTP-FLV | hevc         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | AAC      | HTTP-FLV | hevc         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | G711U    | HTTP-FLV | hevc         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | G722     | HTTP-FLV | hevc         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | G726     | HTTP-FLV | hevc         | AAC          |
| RTSP       | hevc     | 720p/1080p/2k/4k | OPUS     | HTTP-FLV | hevc         | AAC          |
| RTMP       | h264     | 720p/1080p/2k/4k | G711A    | HTTP-FLV | h264         | AAC          |
| RTMP       | h264     | 720p/1080p/2k/4k | AAC      | HTTP-FLV | h264         | AAC          |
| RTMP       | h264     | 720p/1080p/2k/4k | G711U    | HTTP-FLV | h264         | AAC          |





## 如何安装


### 使用docker安装(推荐)


### 使用源码安装


## 视频源转HTTPFLV测试

### 启动RTSP测试程序

### 测试RTSP(UDP模式)转HTTPFLV

### 测试RTSP(TCP模式)转HTTPFLV


### 启动RTMP测试程序

### 测试RTMP转HTTPFLV


## 视频源实时快照测试

### RTSP实时快照测试


### RTMP实时快照测试

