# CAM-HTTPFLV
![License](https://img.shields.io/badge/license-GPLv3.0-blue)
![License](https://img.shields.io/badge/python-3.9-blue)
![License](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/python-3.12-blue)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/zhoukunpeng504/CAM-HTTPFLV/build.yml)
![Flask](https://img.shields.io/badge/Flask-000.svg?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

<p align="left">
         &nbsp 中文 &nbsp | &nbsp;<a href="README.md">English</a> &nbsp 
</p>

CAM-HTTPFLV 支持两大核心功能：
- 把各种格式的RTSP、RTMP视频流转化为HTTPFLV格式的直播视频流(可支持在各种浏览器中访问)
- 对各种格式的RTSP、RTMP视频流进行在线快照，返回jpg格式的图像

在这里，我们简要介绍下CAM-HTTPFLV的支持的视频格式、主要功能以及如何使用。
## 内容
- CAM-HTTPFLV
  - [介绍](#介绍)
  - [支持的视频格式](#支持的视频格式)
  - [如何安装](#如何安装)
    - [使用docker安装(推荐)](#使用docker安装推荐)
    - [使用源码安装](#使用源码安装)
  - [安全认证](#安全认证)
  - [视频源转HTTPFLV直播流](#视频源转httpflv直播流)
  - [视频源实时快照](#视频源实时快照)
    - [RTSP实时快照](#rtsp实时快照测试)
    - [RTMP实时快照](#rtmp实时快照测试)

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

安装前需保证TCP:8005、TCP:8006端口可用(其中8005端口用于HTTPFLV流媒体，8006端口用于对视频源进行快照)。
在这里假设服务器IP为 192.168.1.166。
### 使用docker安装(推荐)
```bash
docker run -itd -p 8005:8005 -p 8006:8006  \
 --restart=always --name=cam-httpflv  \
 zhoukunpeng505/cam-httpflv:latest
```

### 使用源码安装
安装前确保python版本>=3.9.x
```bash
git clone git@github.com:zhoukunpeng504/CAM-HTTPFLV.git
cd  CAM-HTTPFLV
pip3 install -r requirements.txt
python3 server.py
```
### 单元测试与 GitHub Actions

在项目根目录运行（仅使用 Python 标准库，无需安装视频库或启动 Redis）：

```bash
python3 -m unittest discover -s tests -v
```

`.github/workflows/unit-tests.yml` 会在每次 push、pull request 时自动运行，
也可以在 GitHub 的 Actions 页面手动触发，测试 Python 3.10、3.11、3.12。

URL 参数解析位于 `utils/request_parser.py`，由 `server.py` 的 `handle()` 调用。
测试覆盖 URL 编码、嵌套查询参数、`.flv` 后缀、`cam_type` 默认值与校验、
`allow_h265`、重复及空参数，以及错误请求返回 404 和视频任务参数传递。
处理器测试使用 mock 替代视频和网络依赖，不验证实际视频转码或 Redis 通信。

`tests/test_auth.py` 单独覆盖 `PRIVATE_KEY` 开关、必填参数、整数时间戳、
正负 300 秒边界、MD5 格式及签名、URL 编码和两个入口的 403 状态与正文。
HTTP-FLV 和快照共用同一组错误参数用例，检查拒绝访问后不会启动视频任务或快照线程。
Actions 先运行完整测试，再用 Python 优化模式单独运行鉴权测试，
确认关闭 Python 的 `assert` 后鉴权仍然有效。可在本地运行相同命令：

```bash
python3 -O -m unittest discover -s tests -p 'test_auth.py' -v
```

参数沿用现有规则：重复参数采用最后一个非空值；`allow_h265` 缺省或空值为 true，
去除首尾空白后仅 `true`、`1`、`True` 表示启用，其余值均为 false。
摄像头 URL 含 `&`、`+` 等字符时，应先用 `urllib.parse.urlencode` 编码为 `cam_url` 参数。

### 功能1：视频源转HTTPFLV直播流
URL:http://192.168.1.166:8005/?cam_url=XX
- XX: 视频源URL。如:rtsp://192.168.1.166/720p-H264-AAC.mkv、rtmp://192.168.1.166/myapp/720p-H264-AAC.mkv

如何使用？
1. 根据使用场景，拼接url，如：视频源地址为rtmp://192.168.1.166/myapp/720p-H264-AAC.mkv，则转换后的HTTPFLV视频流地址为：
http://192.168.1.166:8005/?cam_url=rtmp://192.168.1.166/myapp/720p-H264-AAC.mkv
2. 将地址填入播放器中，开始播放。目前支持的播放器：VLC、ffplay(ffmpeg)、jessibuca、flv.js


### 功能2：视频源实时快照
URL:http://192.168.1.166:8006/snapshot?cam_url=XX
- XX: 视频源URL。如:rtsp://192.168.1.166/720p-H264-AAC.mkv、rtmp://192.168.1.166/myapp/720p-H264-AAC.mkv
如何使用？
通过GET请求向该地址发起请求即可得到视频源当前的快照图片，格式为jpg。


### 摄像头 URL 的特殊字符编码

当 `cam_url` 中含有 `&`、`+`、`#`、`%`、空格或中文等特殊字符时，
**必须先对参数值进行 URL 编码，再拼接到请求地址中**。
例如，直接拼接的 `&` 会被当作外层查询参数的分隔符，`+` 会被解码为空格，
导致服务端收到的摄像头 URL 与原始地址不一致。
此规则同时适用于 HTTP-FLV 和快照服务，无论是否开启认证。

可以使用 `urllib.parse.urlencode`，直接将原始摄像头 URL 转换为查询参数。例如：

```python
from urllib.parse import urlencode

cam_url = 'rtsp://camera/live?channel=1&token=a+b'
query = urlencode({'cam_url': cam_url})
print('http://192.168.1.166:8005/?' + query)
print('http://192.168.1.166:8006/snapshot?' + query)
```

输出如下（适用于未开启认证时）：

```text
http://192.168.1.166:8005/?cam_url=rtsp%3A%2F%2Fcamera%2Flive%3Fchannel%3D1%26token%3Da%2Bb
http://192.168.1.166:8006/snapshot?cam_url=rtsp%3A%2F%2Fcamera%2Flive%3Fchannel%3D1%26token%3Da%2Bb
```

[开启认证](#安全认证)时，应先使用未经本次 URL 编码的原始 `cam_url` 计算 MD5，
再将 `cam_url`、`time`、`md5` 一起交给 `urlencode` 构造查询参数，具体见下文的认证示例。

## 安全认证

**本仓库默认不启用认证。** 当环境变量 `PRIVATE_KEY` 未设置或为空字符串时，
任何能够访问服务的人都可以请求 HTTP-FLV 视频流和快照，无需提供签名。
本文其他章节中不带签名的访问地址均以这一默认状态为前提。

认证是可选功能，可以独立于其他配置开启。将 `PRIVATE_KEY` 设置为非空字符串，
即可同时为 **8005 端口的 HTTP-FLV 服务和 8006 端口的快照服务**启用认证，
两个服务使用同一个密钥。

源码部署时，按如下方式启动：

```bash
export PRIVATE_KEY='replace-with-your-secret'
python3 server.py
```

使用 Docker 时，先构建包含本功能的镜像，再向容器传入密钥：

```bash
docker build -t cam-httpflv:local .
docker run -d --name cam-httpflv -p 8005:8005 -p 8006:8006 \
  -e PRIVATE_KEY='replace-with-your-secret' cam-httpflv:local
```

如需关闭认证，在启动服务时移除 `PRIVATE_KEY` 或将其设为空字符串即可；
Docker 部署需使用更新后的环境变量重新创建容器。

启用认证后，每次视频流或快照请求的 URL 查询参数必须包含：

- `cam_url`：原始摄像头 URL。签名使用 URL 解码后的值，包括可能存在的 `.flv` 后缀，
  先计算签名，再对其进行 URL 编码以构造请求地址。
- `time`：整数秒级 Unix 时间戳。它与服务器当前时间的差的绝对值必须**严格小于 300 秒**，
  过去和未来的时间戳均受此限制，恰好相差 300 秒时拒绝访问。签名端与服务器应保持时钟同步。
- `md5`：将 `cam_url + str(int(time)) + PRIVATE_KEY` 按顺序拼接，不添加分隔符，
  使用 UTF-8 编码后计算 MD5，取 32 位小写十六进制字符串。

在可信后端中配置与服务端相同的 `PRIVATE_KEY` 环境变量，然后生成带签名的访问地址。
密钥应保留在可信后端，仅将生成的 URL 交给播放器或快照客户端。例如：

```python
import hashlib
import os
import time
from urllib.parse import urlencode

cam_url = 'rtsp://camera/live?channel=1&token=a+b'
timestamp = str(int(time.time()))
private_key = os.environ['PRIVATE_KEY']
signature = hashlib.md5((cam_url + timestamp + private_key).encode('utf-8')).hexdigest()
query = urlencode({'cam_url': cam_url, 'time': timestamp, 'md5': signature})
print('HTTP-FLV:', 'http://192.168.1.166:8005/?' + query)
print('Snapshot:', 'http://192.168.1.166:8006/snapshot?' + query)
```

请替换示例中的摄像头 URL 和服务器地址。`urlencode` 可以保留摄像头 URL 内部的 `&`、`+`
等字符。将生成的 HTTP-FLV 地址填入支持的播放器即可播放；向生成的快照地址发送 GET 请求
即可获取 JPEG 图片。新请求或断线重连时，如果旧时间戳已超出允许范围，需要重新生成签名地址。
认证参数缺失或格式不合法、时间戳超出允许范围、签名不匹配时，均返回 HTTP **403**，
响应正文为 `403`。

## 视频源转HTTPFLV直播流
如下以rtsp://192.168.1.166/2k-H264-G711A.mkv为视频源。
在实际应用中选取rtsp、rtmp协议的视频源均可。
1. 使用ffplay 播放
```bash
ffplay -i 'http://192.168.1.166:8005/?cam_url=rtsp://192.168.1.166/2k-H264-G711A.mkv'
```
<img src="imgs/img66.png" alt="image-20250718084834878" style="width:70%;" />

2. 使用vlc播放
在VLC菜单项中依次点击--File--Open Network
将如下的链接填入输出框：
```bash
http://192.168.1.166:8005/?cam_url=rtsp://192.168.1.166/2k-H264-G711A.mkv
```

<img src="imgs/img_3.png" alt="image-20250718084834878" style="width:70%;" />

然后点击Open


<img src="imgs/img_4.png" alt="image-20250718084834878" style="width:70%;" />

3.使用jessibuca播放
打开如下链接：[jessibuda测试地址](http://jessibuca.monibuca.com/player.html)
在网页中填入播放地址，并点击播放：
```bash
http://192.168.1.166:8005/?cam_url=rtsp://192.168.1.166/2k-H264-G711A.mkv
```

<img src="imgs/img_5.png" alt="image-20250718084834878" style="width:70%;" />


## 视频源实时快照

### RTSP实时快照测试
测试视频源地址是：rtsp://192.168.1.166/2k-H264-G711A.mkv
实时快照地址为：
http://192.168.1.166:8006/snapshot?cam_url=rtsp://192.168.1.166/2k-H264-G711A.mkv


效果预览：

<img src="imgs/img67.png" alt="image-20250718084834878" style="width:70%;" />

### RTMP实时快照测试
测试视频源地址是：rtsp://192.168.1.166/myapp/2k-H264-G711A.mkv
实时快照地址为：
http://192.168.1.166:8006/snapshot?cam_url=rtmp://192.168.1.166/myapp/2k-H264-G711A.mkv


效果预览：


<img src="imgs/img68.png" alt="image-20250718084834878" style="width:80%;" />
