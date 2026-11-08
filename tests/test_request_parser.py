import unittest
from urllib.parse import urlencode

from utils.request_parser import StreamOptions, parse_stream_url


class ParseStreamUrlTests(unittest.TestCase):
    def test_rtsp_defaults(self):
        self.assertEqual(
            parse_stream_url('/?cam_url=rtsp://camera/live'),
            StreamOptions('rtsp://camera/live', 'rtsp-tcp', True),
        )

    def test_rtmp_defaults(self):
        self.assertEqual(
            parse_stream_url('/?cam_url=rtmp://camera/app/live'),
            StreamOptions('rtmp://camera/app/live', 'rtmp', True),
        )

    def test_explicit_transport(self):
        for cam_type in ('rtsp-tcp', 'rtsp-udp', 'rtmp'):
            with self.subTest(cam_type=cam_type):
                options = parse_stream_url('/?' + urlencode({
                    'cam_url': 'rtsp://camera/live', 'cam_type': cam_type,
                }))
                self.assertEqual(options.cam_type, cam_type)

    def test_encoded_camera_url_preserves_credentials_and_query(self):
        cam_url = 'rtsp://user:p+ss%26word@camera:554/视频?token=a+b&channel=1'
        self.assertEqual(
            parse_stream_url('/?' + urlencode({'cam_url': cam_url})).cam_url,
            cam_url,
        )

    def test_camera_url_is_decoded_only_once(self):
        cam_url = 'rtsp://camera/live?token=%26%2B%3D'
        self.assertEqual(
            parse_stream_url('/?' + urlencode({'cam_url': cam_url})).cam_url,
            cam_url,
        )

    def test_split_only_at_first_question_mark(self):
        self.assertEqual(
            parse_stream_url('/?cam_url=rtsp://camera/live?channel=1').cam_url,
            'rtsp://camera/live?channel=1',
        )

    def test_flv_suffix_handling(self):
        cases = (
            ('rtsp://camera/live.flv', 'rtsp://camera/live'),
            ('rtsp://camera/live.flv.flv', 'rtsp://camera/live.flv'),
            ('rtsp://camera/live.FLV', 'rtsp://camera/live.FLV'),
            ('rtsp://camera/live.flv?channel=1', 'rtsp://camera/live.flv?channel=1'),
            ('rtsp://camera/live', 'rtsp://camera/live'),
        )
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(
                    parse_stream_url('/?' + urlencode({'cam_url': source})).cam_url,
                    expected,
                )

    def test_allow_h265_values(self):
        cases = (
            ('true', True), ('1', True), ('True', True), (' true ', True),
            ('false', False), ('0', False), ('False', False),
            ('TRUE', False), ('yes', False), (' ', False),
            ('', True),  # parse_qsl ignores blank values: use the default.
        )
        for value, expected in cases:
            with self.subTest(value=value):
                options = parse_stream_url('/?' + urlencode({
                    'cam_url': 'rtsp://camera/live', 'allow_h265': value,
                }))
                self.assertIs(options.allow_h265, expected)

    def test_blank_transport_uses_protocol_default(self):
        self.assertEqual(
            parse_stream_url('/?cam_url=rtsp://camera/live&cam_type=').cam_type,
            'rtsp-tcp',
        )

    def test_duplicate_parameters_use_last_nonblank_value(self):
        options = parse_stream_url(
            '/?cam_url=rtmp://first/live&cam_url=rtsp://last/live&cam_url='
            '&cam_type=rtsp-tcp&cam_type=rtsp-udp&cam_type='
            '&allow_h265=true&allow_h265=false&allow_h265='
        )
        self.assertEqual(options, StreamOptions('rtsp://last/live', 'rtsp-udp', False))

    def test_unknown_parameters_are_ignored(self):
        self.assertEqual(
            parse_stream_url('/?cam_url=rtsp://camera/live&unknown=value'),
            StreamOptions('rtsp://camera/live', 'rtsp-tcp', True),
        )

    def test_missing_or_blank_cam_url(self):
        for path in ('/', '/?', '/?cam_type=rtsp-tcp', '/?cam_url=', '/?cam_url'):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, '无法找到cam_url参数'):
                    parse_stream_url(path)

    def test_invalid_request_path(self):
        for path in ('/live', '/snapshot', '//', 'http://localhost/'):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, '路径不合法'):
                    parse_stream_url(path + '?cam_url=rtsp://camera/live')

    def test_invalid_transport(self):
        for cam_type in ('http', 'tcp', 'RTSP-TCP', ' rtsp-tcp '):
            with self.subTest(cam_type=cam_type):
                with self.assertRaisesRegex(ValueError, 'cam_type不合法'):
                    parse_stream_url('/?' + urlencode({
                        'cam_url': 'rtsp://camera/live', 'cam_type': cam_type,
                    }))

    def test_cannot_infer_transport(self):
        for cam_url in ('http://camera/live', 'camera/live', 'RTSP://camera/live'):
            with self.subTest(cam_url=cam_url):
                with self.assertRaisesRegex(ValueError, 'cam_type不合法'):
                    parse_stream_url('/?' + urlencode({'cam_url': cam_url}))


if __name__ == '__main__':
    unittest.main()
