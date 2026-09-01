# Jessibuca 本地化 Demo 播放器

参考 jessibuca 官方 demo 播放器（http://jessibuca.monibuca.com/player.html）的功能，
使用 jQuery + Bootstrap 5 重新实现的**完全本地化**版本，页面入口为 `../player.html`。

## 目录结构

```
static/
├── player.html            # 页面入口（相对路径引用以下所有资源）
└── player/
    ├── jessibuca/
    │   ├── jessibuca.js   # jessibuca 内核（GitHub release v3.3.28 的 dist）
    │   ├── decoder.js     # 解码 worker（必须与 decoder.wasm 同目录）
    │   └── decoder.wasm   # ffmpeg wasm 解码器
    ├── vendor/
    │   ├── jquery.min.js          # jQuery 3.7.1
    │   ├── bootstrap.min.css      # Bootstrap 5.3.3
    │   └── bootstrap.bundle.min.js
    ├── css/player.css     # 页面样式（浅色，纯白页面背景）
    └── js/player.js       # 页面逻辑（播放控制、配置、状态、日志）
```

所有资源均为本地文件、相对路径引用，页面运行时无任何外网请求。

## 页面结构

- 顶部为核心播放面板：标题栏 + 播放器 + 缓冲(秒)/开启日志、设置Flv格式/控制栏自动隐藏、
  解码器选择、toggle控制条、输入URL + 播放，与官方 demo player 保持一致；
- 面板下方为地址格式说明；
- 再下方为「更多控制」区域，提供其余操作按钮与配置、状态、日志三个页签。

## 功能

- 播放 / 暂停 / 停止 / 销毁，地址历史记录（localStorage）
- 解码模式切换：MediaSource、WebCodecs、wasm（软解，支持 H264/H265）
- 参数配置：缓冲时长、loading/心跳超时、Flv 格式、控制栏自动隐藏、音频解码、
  默认不静音、网速显示、快捷键、硬解失败降级 wasm、双击全屏、后台自动暂停、
  屏幕常亮、超时自动重播、录制格式；配置修改后重建实例生效
- 运行时操作：静音/取消静音、音量、截图、录制并保存、全屏、清屏、
  toggle 控制条、重设大小、缩放模式、旋转角度
- 状态面板：分辨率与编码、音频信息、fps、音视频码率、缓冲、pts、网速、
  渲染性能、播放时长、首帧耗时、录制时长
- 日志面板：内核事件与错误日志

## 说明

- 支持 `ws-raw`（对接 monibuca）、`ws-flv`、`http-flv` 三种地址，同时支持 wss/https。
- http-flv 存在跨域限制，需要流媒体服务端返回 cors 头。
- MediaSource 模式只支持 H264 视频，且音频需为 MSE 可封装的格式（如 AAC）；
  G711 等音频建议关闭「解码音频」或改用 wasm 模式。
- WebCodecs 模式需要 Chrome 94+ 且为 https 或 localhost 环境。
- 截图功能未直接使用内核的 download 分支（该版本 dist 中该分支有缺陷），
  页面取 base64 后自行触发下载。

## 本地验证

```bash
cd static && python3 -m http.server 8899
```

然后访问 http://127.0.0.1:8899/player.html
