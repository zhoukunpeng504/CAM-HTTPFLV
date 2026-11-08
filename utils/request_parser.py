"""Parse HTTP-FLV URL parameters without loading video or network services."""

from typing import NamedTuple
from urllib.parse import parse_qsl


class StreamOptions(NamedTuple):
    cam_url: str
    cam_type: str
    allow_h265: bool


def parse_stream_url(path: str) -> StreamOptions:
    """Parse the request target using the existing server parameter rules.

    Only '/' is accepted. Blank query values are ignored and the last
    nonblank value wins for repeated parameters, as with dict(parse_qsl()).
    Encode nested camera URLs with urllib.parse.urlencode to preserve '&' and '+'.
    Invalid requests raise ValueError, which the server maps to HTTP 404.
    """
    if '?' not in path:
        raise ValueError('无法找到cam_url参数')
    real_path, query_info = path.split('?', 1)
    if real_path != '/':
        raise ValueError('路径不合法！')

    query_dict = dict(parse_qsl(query_info))
    if not query_dict.get('cam_url'):
        raise ValueError('无法找到cam_url参数')
    cam_url = query_dict['cam_url']
    if cam_url.endswith('.flv'):
        cam_url = cam_url[:-4]

    cam_type = query_dict.get('cam_type', '')
    if not cam_type:
        if cam_url.startswith('rtsp'):
            cam_type = 'rtsp-tcp'
        if cam_url.startswith('rtmp'):
            cam_type = 'rtmp'
    if cam_type not in ('rtsp-tcp', 'rtsp-udp', 'rtmp'):
        raise ValueError('cam_type不合法')

    allow_h265 = query_dict.get('allow_h265', 'true').strip()
    return StreamOptions(cam_url, cam_type, allow_h265 in ('true', '1', 'True'))
