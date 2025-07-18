# coding:utf-8
# write by zkp
import copy
import random
from gevent.monkey import patch_all; patch_all()
import gevent
import re
from urllib import parse
import base64
import hashlib,struct, time
import psutil
from utils import _av_, process_task
import os
import setproctitle
import redis
import json
from gevent import threading
import datetime
import flask
import flask_cors
from flask import Flask,Response,request,jsonify
from flask_cors import CORS
import gzip
import av
import cv2
from gevent.queue import Queue
import traceback


app = Flask(__name__, #template_folder=os.path.join(BASE_PATH, 'templates'),
            #static_folder=os.path.join(BASE_PATH, 'static'),
            #static_url_path = '/static'
            )
app.debug = True
# 允许跨域
CORS(app)


def JsonResponse(data):
    print("request.form", list(request.form.items()))
    print("JsonResponse", data)
    coding = request.headers.get('Accept-Encoding', '')
    if 'gzip' in coding:
        resp = Response(gzip.compress(json.dumps(data).encode('utf-8')),
                        mimetype='application/json')
        resp.headers['Content-Encoding'] = 'gzip'
    else:
        resp = Response(json.dumps(data), mimetype='application/json')
    return resp


redis_url = None
current_path = os.path.abspath(os.path.dirname(__file__))


def print_to_logger(*args):
    now = datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')
    try:
        msg = " ".join([str(i) for i in args ])
        print(f"[{now}: INFO]:{msg}")
    except:
        pass


class Header(object):
    __slots__ = ('fin', 'mask', 'opcode', 'flags', 'length')

    FIN_MASK = 0x80
    OPCODE_MASK = 0x0f
    MASK_MASK = 0x80
    LENGTH_MASK = 0x7f

    RSV0_MASK = 0x40
    RSV1_MASK = 0x20
    RSV2_MASK = 0x10

    # bitwise mask that will determine the reserved bits for a frame header
    HEADER_FLAG_MASK = RSV0_MASK | RSV1_MASK | RSV2_MASK

    def __init__(self, fin=0, opcode=0, flags=0, length=0):
        self.mask = ''
        self.fin = fin
        self.opcode = opcode
        self.flags = flags
        self.length = length

    def mask_payload(self, payload):
        payload = bytearray(payload)
        mask = bytearray(self.mask)

        for i in range(self.length):
            payload[i] ^= mask[i % 4]

        return payload

    # it's the same operation
    unmask_payload = mask_payload

    def __repr__(self):
        opcodes = {
            0: 'continuation(0)',
            1: 'text(1)',
            2: 'binary(2)',
            8: 'close(8)',
            9: 'ping(9)',
            10: 'pong(10)'
        }
        flags = {
            0x40: 'RSV1 MASK',
            0x20: 'RSV2 MASK',
            0x10: 'RSV3 MASK'
        }

        return ("<Header fin={0} opcode={1} length={2} flags={3} mask={4} at "
                "0x{5:x}>").format(
                    self.fin,
                    opcodes.get(self.opcode, 'reserved({})'.format(self.opcode)),
                    self.length,
                    flags.get(self.flags, 'reserved({})'.format(self.flags)),
                    self.mask, id(self)
        )

    @classmethod
    def decode_header(cls, stream):
        """
        Decode a WebSocket header.

        :param stream: A file like object that can be 'read' from.
        :returns: A `Header` instance.
        """
        read = stream.read
        data = read(2)

        if len(data) != 2:
            raise Exception("Unexpected EOF while decoding header")

        first_byte, second_byte = struct.unpack('!BB', data)

        header = cls(
            fin=first_byte & cls.FIN_MASK == cls.FIN_MASK,
            opcode=first_byte & cls.OPCODE_MASK,
            flags=first_byte & cls.HEADER_FLAG_MASK,
            length=second_byte & cls.LENGTH_MASK)

        has_mask = second_byte & cls.MASK_MASK == cls.MASK_MASK

        if header.opcode > 0x07:
            if not header.fin:
                raise Exception(
                    "Received fragmented control frame: {0!r}".format(data))

            # Control frames MUST have a payload length of 125 bytes or less
            if header.length > 125:
                raise Exception(
                    "Control frame cannot be larger than 125 bytes: "
                    "{0!r}".format(data))

        if header.length == 126:
            # 16 bit length
            data = read(2)

            if len(data) != 2:
                raise Exception('Unexpected EOF while decoding header')

            header.length = struct.unpack('!H', data)[0]
        elif header.length == 127:
            # 64 bit length
            data = read(8)

            if len(data) != 8:
                raise Exception('Unexpected EOF while decoding header')

            header.length = struct.unpack('!Q', data)[0]

        if has_mask:
            mask = read(4)

            if len(mask) != 4:
                raise Exception('Unexpected EOF while decoding header')

            header.mask = mask

        return header

    @classmethod
    def encode_header(cls, fin, opcode, mask, length, flags):
        """
        Encodes a WebSocket header.

        :param fin: Whether this is the final frame for this opcode.
        :param opcode: The opcode of the payload, see `OPCODE_*`
        :param mask: Whether the payload is masked.
        :param length: The length of the frame.
        :param flags: The RSV* flags.
        :return: A bytestring encoded header.
        """
        first_byte = opcode
        second_byte = 0
        extra = b""
        result = bytearray()

        if fin:
            first_byte |= cls.FIN_MASK

        if flags & cls.RSV0_MASK:
            first_byte |= cls.RSV0_MASK

        if flags & cls.RSV1_MASK:
            first_byte |= cls.RSV1_MASK

        if flags & cls.RSV2_MASK:
            first_byte |= cls.RSV2_MASK

        # now deal with length complexities
        if length < 126:
            second_byte += length
        elif length <= 0xffff:
            second_byte += 126
            extra = struct.pack('!H', length)
        elif length <= 0xffffffffffffffff:
            second_byte += 127
            extra = struct.pack('!Q', length)
        else:
            raise Exception("too large frame")

        if mask:
            second_byte |= cls.MASK_MASK

        result.append(first_byte)
        result.append(second_byte)
        result.extend(extra)

        if mask:
            result.extend(mask)

        return result


def handle(sock, address):
    global CONFIG_JSON
    print_to_logger("connected", sock, address)
    request_data_raw = sock.recv(10240)
    print_to_logger(request_data_raw)
    try:
        request_data = request_data_raw.decode("utf-8").splitlines()
        base_info = request_data[0]
        _a,_b,_c = base_info.split()
        if _a == 'GET':
            path = _b
            print_to_logger("path", path)
            real_path, query_info = path.split("?", 1) #[1]
            assert real_path in ("/",), Exception("路径不合法！")
            query_dict = dict(parse.parse_qsl(query_info))
            assert "cam_url" in query_dict and query_dict['cam_url'],\
                Exception('无法找到cam_url参数')
            cam_url = query_dict['cam_url']#.strip(".flv")
            if cam_url.endswith(".flv"):
                cam_url = cam_url[:-4]
            #assert 'cam_type' in query_dict and query_dict['cam_url'],  Exception('无法找到cam_type参数')
            cam_type = query_dict.get('cam_type', '')
            if not cam_type:
                if cam_url.startswith("rtsp"):
                    cam_type = "rtsp-tcp"
                if cam_type.startswith("rtmp"):
                    cam_type = "rtmp"
            assert cam_type in ("rtsp-tcp", 'rtsp-udp', "rtmp"), Exception("cam_type不合法")
            allow_h265 = query_dict.get('allow_h265', 'true').strip()
            if allow_h265 in ('true', '1', 'True'):
                allow_h265 = True
            else:
                allow_h265 = False

            # assert cam_url.startswith("rtsp://")
            _ = [[j.strip() for j in i.split(":", 1)] for i in request_data[1:]]
            headers = dict([i for i in _ if len(i) == 2])
            if headers.get("Upgrade") == 'websocket':
                is_websocket = True
                ws_key = headers.get('Sec-WebSocket-Key', '')
            else:
                is_websocket = False
                ws_key = ''
            print_to_logger(headers, is_websocket, ws_key, cam_url)
        else:
            raise Exception("must be GET!")
        print_to_logger(request_data)
    except Exception as e:
        print_to_logger("ERROR!!", str(e))
        print_to_logger(traceback.format_exc())
        sock.send(b"HTTP/1.1 404 Not Found\r\n\r\nNot Found")
    else:
        if not is_websocket:
            sock.send(b"HTTP/1.1 200 OK\r\n" +
                      b"Access-Control-Allow-Methods: GET, OPTIONS\r\n"+
                      b"Access-Control-Allow-Origin: *\r\n"+
                      b"Access-Control-Allow-Credentials: true\r\n" +
                      b"Content-Type: video/x-flv\r\n"+
                      b"\r\n")
        else:
            msg = b'HTTP/1.1 101 Switching Protocols\r\n' + \
                  b'Upgrade: websocket\r\n' + \
                  b'Connection: Upgrade\r\n' + \
                  (b'Sec-WebSocket-Accept: %s\r\n\r\n' % base64.b64encode(hashlib.sha1(ws_key.encode() +
                                                                b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest()))
            # print_to_logger(msg)
            sock.send(msg)
        # queue = multiprocessing.Queue(maxsize=150)
        # 模式选择
        # mode = 'TCP'
        # print_to_logger("xx", g_store.get("cameras_mode",{}))
        # cameras_replace_data = g_store.get("cameras_replace", {})
        # cameras = g_store.get('cameras', [])
        # cam_type = cam_obj['cam_type']
        print_to_logger("cam_url", cam_url, cam_type)
        # if cam_type not in ('rtsp-tcp', 'rtsp-udp', 'rtmp'):
        #    return
        queue_key = f"httpflv_queue_{random.random()}"
        task_id = process_task.run_task(fun=_av_.av_function, args=(cam_url,redis_url, queue_key, os.getpid()),
                                        kwargs={'cam_type': cam_type,
                                                'config_json': CONFIG_JSON,
                                                'enable_auto_encode': not allow_h265
                                                })
        redis_conn = redis.Redis.from_url(redis_url)
        last_data_time = int(time.time())
        while 1:
            # print_to_logger(dir(sock))
            if sock.closed or time.time() - last_data_time > 8:
                # 如果socket被关闭 或者 超过8秒未获取到数据
                print_to_logger("end.....")
                break
            try:
                info = redis_conn.lpop(queue_key)
                assert len(info) > 0
                # gevent.sleep(0.001)
            except Exception as e:
                gevent.sleep(0.1)
            else:
                last_data_time = time.time()
                print_to_logger("send_data")
                if not is_websocket:
                    try:
                        sock.sendall(info)
                    except Exception as e:
                        print_to_logger("sock.sendall error", str(e))
                        break
                else:
                    header = Header.encode_header(True, 0x02, b'', len(info), 0)
                    try:
                        sock.sendall(header+info)
                    except Exception as e:
                        print_to_logger("sock.sendall error", str(e))
                        break
        print_to_logger("kill")
        try:
            with open(f"/tmp/process_task/pids/{task_id}", "r") as f:
                worker_pid = int(f.read())
        except:
            print_to_logger("cant find pid!")
        else:
            def clean_sub_process(worker_pid):
                try:
                    p_obj = psutil.Process(pid=worker_pid)
                    p_obj.send_signal(9)
                    p_obj.kill()
                except Exception as e:
                    print_to_logger(str(e))
                    pass
                try:
                    p_obj.wait(timeout=3)
                except:
                    pass
            _t = threading.Thread(target=clean_sub_process, args=(worker_pid,), daemon=True)
            _t.start()
        redis_conn.delete(queue_key)
        redis_conn.close()


@app.route("/snapshot", methods=['GET', 'POST'])
def snapshot():
    # 获取摄像头当前图像
    cam_url = request.args.get("cam_url", '')
    if not cam_url:
        return Response(b'', mimetype="image/jpeg",
                        status=404)
    que_ = Queue(maxsize=1)
    def get_snapshot(cam_url=copy.deepcopy(cam_url)):
        try:
            # 模式选择
            try:
                video = av.open(cam_url, 'r',
                                metadata_errors='ignore',
                                timeout=2,
                                container_options=({
                                    "buffer_size": "1024000",
                                    "rtsp_transport": "tcp",
                                    "stimeout": "20000000",
                                    "max_delay": "3000000",
                                    "probesize": "100000",
                                    "analyzeduration": "150000"
                                  } if 'rtsp' in cam_url else {
                                    "buffer_size": "1024000",
                                    "stimeout": "20000000",
                                    "max_delay": "3000000",
                                    "probesize": "300000",
                                    "analyzeduration": "350000"
                                })
                                )
                stream = video.streams.video[0]
                # stream.codec_context.skip_frame = 'NONKEY'
                stream.codec_context.options = {
                    'tune': 'zerolatency',
                }
                for frame in video.decode(stream):
                    img = frame.to_ndarray(format='bgr24').copy()
                    jpg_image_bytes = bytes(cv2.imencode(".jpg", img)[1])
                    # os.system("rm -rf %s_*" % os.path.join(snap_dir,cam_md5))
                    # 把时间戳 和 图片内容存入redis
                    que_.put(jpg_image_bytes)
                    break
                video.close()
                del video
            except Exception as e:
                print_to_logger("line 81 except!", str(e))
            finally:
                try:
                    video.close()
                except:
                    pass
                try:
                    del video
                except:
                    pass
        except Exception as e:
            print_to_logger("snap shot err!!", str(e))
        return

    thr = threading.Thread(target=get_snapshot, args=(cam_url,), daemon=True)
    thr.start()
    try:
        with gevent.Timeout(5) :
            data = que_.get(block=True)
    except (Exception,BaseException,gevent.Timeout) as e:
        print_to_logger(str(e))
        return Response(b'', mimetype='image/jpeg', status=404)
    else:
        return Response(data, mimetype="image/jpeg", status=200)


if __name__ == '__main__':
    httpflv_bind_ip = '0.0.0.0'
    httpflv_port = 8005
    setproctitle.setproctitle('rtsp_flv')
    redis_url = os.environ.get("REDIS_URL", 'redis://127.0.0.1:6379/8').strip()
    try:
        assert redis.Redis.from_url(redis_url).ping() == True
    except:
        raise Exception("redis 无法连接！" + redis_url)
    with open("config.json", "r") as f:
        CONFIG_JSON = json.loads(f.read())
    print_to_logger("Start HttpFlv Server", 'http://0.0.0.0:%s/' % httpflv_port)
    from gevent.server import StreamServer
    from gevent.pywsgi import WSGIServer
    server = StreamServer(('0.0.0.0', int(httpflv_port)), handle)
    http_server = WSGIServer(('0.0.0.0', 8006), app)
    http_server.start()
    print_to_logger("Start Snapshot Server", "http://0.0.0.0:8006/")
    server.serve_forever()
