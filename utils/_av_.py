# coding:utf-8
__author__ = "zkp"
# create by zkp on 2022/9/14
import os


def av_function(cam_url, redis_url,
                queue_key, main_process_pid, cam_type,
                config_json:dict = {},
                enable_auto_encode=True
                ):
    import time, av
    av.logging.set_level(av.logging.CRITICAL)
    print("start av_ function", time.time())
    import time
    import sys
    import redis, datetime, os, traceback, random, string
    import psutil
    # import ctypes
    sys.path.append(os.path.abspath(os.path.dirname(__file__)))
    try:
        import md5
    except:
        from . import md5
    # 删除老的标识文件
    cam_url_md5 = md5.md5(cam_url)
    hook_mark_path = f"/tmp/{cam_url_md5}"
    os.system(f"rm -rf {hook_mark_path}")
    import setproctitle
    setproctitle.setproctitle("rtsp_httpflv")
    main_p = psutil.Process(main_process_pid)

    def print_to_logger(*args):
        "日志函数"
        file_name = os.path.join("/data/logs",
                                 f"httpflv-av-{datetime.datetime.now().strftime('%Y%m%d')}.log")
        now = datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')
        try:
            msg = " ".join([str(i) for i in args])
            with open(file_name, "a+") as f:
                f.write(f"[{now}: INFO]:{msg}\n")
        except:
            pass

    redis_conn = redis.Redis.from_url(redis_url)
    redis_conn.delete(queue_key)

    class FileObj(object):
        def __init__(self, name):
            self.name = name
            self.key = queue_key
            self.buff = b''
            self.last_time = time.time()

        def write(self, info: bytes):
            print_to_logger("write ....")
            _t = time.time()
            self.buff += info
            if _t - self.last_time > 0.1:  # 超过0.1秒
                try:
                    redis_conn.rpush(self.key, self.buff)
                    # print("write to redis", len(self.buff))
                except Exception as e:
                    print_to_logger("put failed")
                    print_to_logger(traceback.format_exc())
                self.buff = b''
                self.last_time = _t

        def qsize(self):
            try:
                # return self.queue.qsize()
                return redis_conn.llen(self.key)
            except:
                return 0

    assert cam_type in ('rtsp-tcp', 'rtsp-udp', 'rtmp')
    kwargs = config_json['FFMPEG_OPTIONS'].get(cam_type.upper(), {})
    print_to_logger(cam_url, cam_type, kwargs)
    counter = 0
    while 1:
        try:
            print_to_logger("av open", cam_url)
            #counter += 1
            video = av.open(cam_url, 'r',
                            # format,
                            # options=dicOption,
                            metadata_errors='ignore',
                            # format=format,
                            **kwargs
                            )
            print_to_logger("av open ...")
            # packet_num = 0
            stream = video.streams.video[0]
            try:
                audio = video.streams.audio[0]
                audio_code_name = audio.codec_context.name
            except:
                audio = None
                audio_code_name = ''
            print_to_logger("video # audio", stream, audio)
            # print(stream.codec_context)
            # print(dir(stream.codec_context), stream.codec_context.name)
            code_name = stream.codec_context.name
            print_to_logger("code", code_name)
            _ = FileObj("11.flv")
            output = av.open(_, 'w'  # ,  # options={'buffer_size': '9024000'}
                             )
            need_encode = False
            if code_name in ('h265', 'hevc') and enable_auto_encode:
                _out_stream = output.add_stream(codec_name='h264', rate=stream.codec_context.framerate)
                _out_stream.width = 1920
                _out_stream.height = 1080
                need_encode = True
            else:
                _out_stream = output.add_stream(codec_name=code_name, rate=stream.codec_context.framerate)
                _out_stream.width = stream.width
                _out_stream.height = stream.height

            _out_stream.codec_context.options = {
                # 'tune': 'zerolatency',
                'preset': 'ultrafast'
            }
            if audio:
                print("audio time base", audio.time_base,audio.codec_context, audio.codec_context.rate)
                # 源视频中含有音频流
                _out_stream_audio = output.add_stream(codec_name='pcm_alaw',
                                                      rate=8000, #audio.codec_context.rate,
                                                      layout=audio.codec_context.layout.name,
                                                      )  # layout和输入保持一致
                _out_stream_audio.time_base = '1/8000' #str(audio.time_base) #'1/8000'
            else:
                _out_stream_audio = None

            # _out_stream_audio = None

            for _p in video.demux():  # , **({"audio":0} if _out_stream_audio else {}
                counter += 1
                if _p.pts == None:
                    _p.pts = 0
                    _p.dts = 0
                if _p.stream_index == 0:
                    # 视频帧
                    if not need_encode:
                        # 无需转码
                        try:
                            # _out_stream.width = 960
                            # _out_stream.height = 540
                            # print(frame)
                            # _packets = _out_stream.encode(frame)
                            # for _p in _packets:
                            # _p.time_base = '1/90000'
                            # _p.dts = _time
                            # _p.pts = _time
                            # print(_p)
                            # print(_p, _p.time_base, _p.dts, _p.pts)
                            time_base = _p.time_base
                            last_pts = _p.pts
                            output.mux(_p)
                        except (Exception, BaseException) as e:
                            print_to_logger("mux except:", str(e))
                    else:
                        # 需要转码
                        frames = _p.decode()
                        for frame in frames:
                            counter += 1
                            try:
                                # _out_stream.width = 960
                                # _out_stream.height = 540
                                # print(frame)
                                _packets = _out_stream.encode(frame)
                                for _p in _packets:
                                    _p.time_base = '1/90000'
                                    _p.dts = frame.pts
                                    _p.pts = frame.pts
                                    _p.stream = _out_stream
                                    # print(_p)
                                    output.mux(_p)
                            except (Exception, BaseException) as e:
                                print_to_logger("decode and mux except:", str(e))

                if _p.stream_index == 1 and _out_stream_audio:
                    # 音频帧
                    if audio_code_name == 'pcm_alaw':
                        try:
                            # print(_p, _p.time_base, _p.dts, _p.pts)
                            _p.stream = _out_stream_audio
                            output.mux(_p)
                        except Exception as e:
                            print_to_logger("mux audio except:", str(e))
                    else:
                        _p_ = _p.decode()
                        if _p_:
                            try:
                                kks = _out_stream_audio.encode(_p_[0])
                                print(_p_, kks)
                                for kk in kks:
                                    kk.stream = _out_stream_audio
                                    output.mux(kk)
                            except Exception as e:
                                print_to_logger("mux audio except:", str(e))

                # 主进程是否存活判断
                if counter % 10 == 0:
                    try:
                        assert main_p.name() == 'rtsp_flv'
                    except Exception:
                        print_to_logger(main_p, main_p.pid, main_p.name(), "!=rtsp_flv")
                        sys.exit(0)


        except (Exception, BaseException, AttributeError) as e:
            print_to_logger("#######", str(e))
            traceback.print_exc()
        finally:
            try:
                video.close()
            except:
                pass
            try:
                output.close()
            except:
                pass

            #if counter % 10 == 0:
            try:
                assert main_p.name() == 'rtsp_flv'
            except Exception:
                print_to_logger(main_p, main_p.pid, main_p.name(), "!=rtsp_flv")
                sys.exit(0)

