# coding:utf-8
__author__ = "zkp"
# create by zkp on 2022/9/14
import os
from av import bitstream


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
    from av import bitstream
    import fractions
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
    mp4toannexb_filter = None
    while 1:
        try:
            print_to_logger("av open", cam_url)
            # counter += 1
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
            if cam_type == 'rtmp':
                mp4toannexb_filter = bitstream.BitStreamFilterContext("h264_mp4toannexb",
                                                                      in_stream=stream)
            try:
                audio = video.streams.audio[0]
                audio_code_name = audio.codec_context.name
            except:
                audio = None
                audio_code_name = ''
            print_to_logger("video # audio", stream,
                            stream.time_base ,stream.codec_context.framerate,
                            audio)
            # print(stream.codec_context)
            # print(dir(stream.codec_context), stream.codec_context.name)
            code_name = stream.codec_context.name
            print_to_logger("code", code_name)
            _ = FileObj("11.flv")
            output = av.open(_, 'w'  # ,  # options={'buffer_size': '9024000'}
                             )
            need_encode = False
            if code_name in ('h265', 'hevc') and enable_auto_encode:
                _out_stream = output.add_stream(codec_name='h264',
                                                rate=stream.codec_context.framerate
                                                )
                _out_stream.width = 1920
                _out_stream.height = 1080
                need_encode = True
            else:
                _out_stream = output.add_stream(codec_name=code_name,
                                                rate=stream.codec_context.framerate
                                                )
                _out_stream.width = stream.width
                _out_stream.height = stream.height

            _out_stream.time_base = fractions.Fraction(1, 1000) #'1/1000'
            # time_base对齐

            _out_stream.codec_context.options = {
                # 'tune': 'zerolatency',
                'preset': 'ultrafast'
            }
            if audio:
                print("audio time base", audio.time_base,audio.codec_context, audio.codec_context.rate,
                      audio.codec_context.layout.name)
                # 源视频中含有音频流
                _out_stream_audio = output.add_stream(codec_name='aac',
                                                      rate=audio.codec_context.rate,#8000, #audio.codec_context.rate,
                                                      layout=audio.codec_context.layout.name,
                                                      )  # layout和输入保持一致

                # _out_stream_audio.time_base = f"1/{audio.codec_context.rate}"
                # '1/8000' #str(audio.time_base) #'1/8000'
                # f'1/{str(audio.time_base).split("/")[-1]}'
                _out_stream_audio.time_base = fractions.Fraction(1, audio.time_base.denominator)
            else:
                _out_stream_audio = None

            # _out_stream_audio = None

            for _p in video.demux():  # , **({"audio":0} if _out_stream_audio else {}
                counter += 1
                if _p.pts == None or _p.pts==0 or _p.dts==0:
                    _p.pts = 1
                    _p.dts = 1

                # if _p.pts and _p.dts and _p.pts > _p.dts:
                #     _p.dts = _p.pts
                print("[_p]", _p, _p.stream)

                if 'video' in str(_p.stream.codec_context):
                    # 处理RTMP格式的 packet包格式(AVCC)问题。 转化为annexb格式
                    if cam_type == 'rtmp':
                        _p = mp4toannexb_filter.filter(_p)[0]
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
                            print("[VIDEO]", _p, _p.time_base, _p.dts, _p.pts,_p.is_keyframe)
                            #_time = int(_p.dts / 90)
                            #_p.dts = _time
                            #_p.pts = _time
                            # print(_p)
                            # print("[VIDEO]",_p, _p.time_base, _p.dts, _p.pts)
                            #_p.time_base = _p.time_base / 90
                            # last_pts = _p.pts
                            _p.stream = _out_stream
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
                                    # _p.time_base = '1/1000'
                                    _p.dts = frame.pts
                                    _p.pts = frame.pts
                                    _p.stream = _out_stream
                                    # print(_p)
                                    output.mux(_p)
                            except (Exception, BaseException) as e:
                                print_to_logger("decode and mux except:", str(e))

                # if _p.stream_index == 1 and _out_stream_audio:
                elif 'audio' in str(_p.stream.codec_context) and _out_stream_audio:
                    # 音频帧
                    print("[AUDIO]", _p, _p.time_base, _p.dts, _p.pts)
                    if audio_code_name == 'aac' and str(audio.codec_context.rate) == '8000':
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
                                # print(_p_, kks)
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

