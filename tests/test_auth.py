"""Test PRIVATE_KEY authentication and access control on both service endpoints."""

import hashlib
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from server_test_support import ServerTestCase


class AuthorizationTests(ServerTestCase):
    def signed_params(self, timestamp=1700000000, cam_url='rtsp://camera/live.flv',
                      private_key='test-key'):
        timestamp = str(timestamp)
        signature = hashlib.md5(
            (cam_url + timestamp + private_key).encode('utf-8')
        ).hexdigest()
        return {'cam_url': cam_url, 'time': timestamp, 'md5': signature}

    def enable_auth(self):
        os.environ['PRIVATE_KEY'] = 'test-key'
        self.context.enter_context(patch.object(
            self.server.time, 'time', return_value=1700000000,
        ))

    def stream_request(self, params):
        return ('GET /?' + urlencode(params) + ' HTTP/1.1\r\n\r\n').encode()

    def invalid_auth_params(self):
        """Exercise identical rejection cases through both service entry points."""
        for name in ('cam_url', 'time', 'md5'):
            params = self.signed_params()
            del params[name]
            yield 'missing ' + name, params
            params = self.signed_params()
            params[name] = ''
            yield 'blank ' + name, params

        for value in ('bad', 'NaN', 'inf', '1700000000.5', '1e9', '-1', '9' * 1000):
            params = self.signed_params()
            params['time'] = value
            yield 'invalid time ' + value[:20], params

        for value in ('a' * 31, 'a' * 33, 'g' * 32, '0' * 32,
                      self.signed_params()['md5'].upper(), '中' * 32, 'a' * 31 + '\n'):
            params = self.signed_params()
            params['md5'] = value
            yield 'invalid md5 ' + repr(value), params

        for offset in (-301, -300, 300, 301):
            yield 'time offset ' + str(offset), self.signed_params(1700000000 + offset)

        yield 'wrong private key', self.signed_params(private_key='wrong-key')
        for name, value in (('cam_url', 'rtsp://other/live.flv'), ('time', '1700000001')):
            params = self.signed_params()
            params[name] = value
            yield 'tampered ' + name, params

    def assert_stream_forbidden(self, params):
        sock = self.make_socket(self.stream_request(params))
        self.server.handle(sock, ('127.0.0.1', 12345))
        sock.send.assert_not_called()
        sock.sendall.assert_called_once()
        headers, body = sock.sendall.call_args.args[0].split(b'\r\n\r\n', 1)
        self.assertTrue(headers.startswith(b'HTTP/1.1 403 Forbidden\r\n'))
        self.assertEqual(body, b'403')
        self.server.process_task.run_task.assert_not_called()
        self.server.redis.Redis.from_url.assert_not_called()

    def test_auth_disabled_for_empty_or_unset_private_key(self):
        for key in ('', None):
            with self.subTest(private_key=key):
                if key is None:
                    os.environ.pop('PRIVATE_KEY', None)
                else:
                    os.environ['PRIVATE_KEY'] = key
                self.assertTrue(self.server.is_request_authorized({}))
                self.assertTrue(self.server.is_request_authorized({
                    'time': 'invalid', 'md5': 'invalid',
                }))

    def test_auth_matches_fixed_md5_test_vector(self):
        self.enable_auth()
        self.assertTrue(self.server.is_request_authorized({
            'cam_url': 'rtsp://camera/live.flv',
            'time': '1700000000',
            'md5': 'bb2124d65841362fe28dbd3a41ae3f5c',
        }))

    def test_auth_time_window_is_strictly_less_than_300_seconds(self):
        self.enable_auth()
        for offset, expected in ((-301, False), (-300, False), (-299, True),
                                 (0, True), (299, True), (300, False), (301, False)):
            with self.subTest(offset=offset):
                self.assertIs(self.server.is_request_authorized(
                    self.signed_params(1700000000 + offset),
                ), expected)

    def test_auth_uses_fractional_server_time_without_truncation(self):
        self.enable_auth()
        self.server.time.time.return_value = 1700000000.5
        self.assertFalse(self.server.is_request_authorized(self.signed_params(1699999700)))
        self.assertTrue(self.server.is_request_authorized(self.signed_params(1699999701)))
        self.assertTrue(self.server.is_request_authorized(self.signed_params(1700000300)))

    def test_auth_rejects_missing_parameters(self):
        self.enable_auth()
        for name in ('cam_url', 'time', 'md5'):
            with self.subTest(missing=name):
                params = self.signed_params()
                del params[name]
                self.assertFalse(self.server.is_request_authorized(params))

    def test_auth_rejects_invalid_timestamps(self):
        self.enable_auth()
        for value in ('', 'bad', 'NaN', 'inf', '1700000000.5', '1e9',
                      '-1', '9' * 1000, None):
            with self.subTest(time=value):
                params = self.signed_params()
                params['time'] = value
                self.assertFalse(self.server.is_request_authorized(params))

    def test_auth_normalizes_integer_timestamp_before_signing(self):
        self.enable_auth()
        params = self.signed_params()
        params['time'] = '01700000000'
        self.assertTrue(self.server.is_request_authorized(params))

    def test_auth_rejects_malformed_or_wrong_md5(self):
        self.enable_auth()
        valid = self.signed_params()['md5']
        for signature in ('', 'a' * 31, 'a' * 33, 'g' * 32, '0' * 32,
                          valid.upper(), '中' * 32, valid + '\n'):
            with self.subTest(md5=signature):
                params = self.signed_params()
                params['md5'] = signature
                self.assertFalse(self.server.is_request_authorized(params))

    def test_auth_signature_binds_cam_url_timestamp_and_private_key(self):
        self.enable_auth()
        for change in ({'cam_url': 'rtsp://other/live.flv'},
                       {'time': '1700000001'}, {'md5': self.signed_params(
                           private_key='wrong-key')['md5']}):
            with self.subTest(change=change):
                params = self.signed_params()
                params.update(change)
                self.assertFalse(self.server.is_request_authorized(params))

    def test_nonempty_private_key_is_not_stripped(self):
        self.enable_auth()
        os.environ['PRIVATE_KEY'] = ' '
        self.assertFalse(self.server.is_request_authorized({}))
        self.assertTrue(self.server.is_request_authorized(
            self.signed_params(private_key=' '),
        ))

    def test_signed_stream_starts_worker_after_auth(self):
        self.enable_auth()
        params = self.signed_params()
        sock = self.make_socket(self.stream_request(params))
        self.server.handle(sock, ('127.0.0.1', 12345))
        self.assertTrue(sock.send.call_args.args[0].startswith(b'HTTP/1.1 200 OK'))
        self.server.process_task.run_task.assert_called_once()
        self.assertEqual(
            self.server.process_task.run_task.call_args.kwargs['args'][0],
            'rtsp://camera/live',
        )

    def test_signed_stream_uses_decoded_original_camera_url(self):
        self.enable_auth()
        cam_url = 'rtsp://user:p+ss%26@camera/视频.flv?token=a+b&channel=1'
        sock = self.make_socket(self.stream_request(self.signed_params(cam_url=cam_url)))
        self.server.handle(sock, ('127.0.0.1', 12345))
        self.assertTrue(sock.send.call_args.args[0].startswith(b'HTTP/1.1 200 OK'))
        self.assertEqual(
            self.server.process_task.run_task.call_args.kwargs['args'][0], cam_url,
        )

    def test_stream_rejects_unsigned_or_invalid_requests_before_work(self):
        self.enable_auth()
        for case, params in self.invalid_auth_params():
            with self.subTest(case=case):
                self.assert_stream_forbidden(params)

    def test_stream_accepts_auth_inside_time_window(self):
        self.enable_auth()
        for offset in (-299, 0, 299):
            with self.subTest(offset=offset):
                self.server.process_task.run_task.reset_mock()
                sock = self.make_socket(self.stream_request(
                    self.signed_params(1700000000 + offset),
                ))
                self.server.handle(sock, ('127.0.0.1', 12345))
                self.assertTrue(sock.send.call_args.args[0].startswith(b'HTTP/1.1 200 OK'))
                self.server.process_task.run_task.assert_called_once()

    def test_stream_cannot_sign_the_stripped_camera_url(self):
        self.enable_auth()
        params = self.signed_params(cam_url='rtsp://camera/live')
        params['cam_url'] += '.flv'
        self.assert_stream_forbidden(params)

    def test_snapshot_rejects_invalid_auth_before_opening_camera(self):
        self.enable_auth()
        for case, params in self.invalid_auth_params():
            with self.subTest(case=case):
                self.server.request.args = params
                self.server.Response.reset_mock()
                response = self.server.snapshot()
                self.server.Response.assert_called_once_with(
                    '403', mimetype='text/plain', status=403,
                )
                self.assertIs(response, self.server.Response.return_value)
        self.server.Queue.assert_not_called()
        self.server.threading.Thread.assert_not_called()
        self.server.av.open.assert_not_called()

    def test_snapshot_accepts_auth_inside_time_window(self):
        self.enable_auth()
        self.server.Queue.return_value.get.return_value = b'jpeg-data'
        for offset in (-299, 0, 299):
            with self.subTest(offset=offset):
                self.server.Response.reset_mock()
                self.server.threading.Thread.reset_mock()
                self.server.request.args = self.signed_params(1700000000 + offset)
                self.server.snapshot()
                self.server.Response.assert_called_once_with(
                    b'jpeg-data', mimetype='image/jpeg', status=200,
                )
                self.server.threading.Thread.assert_called_once()

    def test_snapshot_accepts_valid_signature(self):
        self.enable_auth()
        params = self.signed_params(cam_url='rtsp://camera/视频?token=a+b&channel=1')
        self.server.request.args = params
        self.server.Queue.return_value.get.return_value = b'jpeg-data'
        self.server.snapshot()
        self.server.threading.Thread.assert_called_once()
        self.assertEqual(
            self.server.threading.Thread.call_args.kwargs['args'], (params['cam_url'],),
        )
        self.server.Response.assert_called_once_with(
            b'jpeg-data', mimetype='image/jpeg', status=200,
        )

    def test_snapshot_remains_accessible_when_auth_is_disabled(self):
        self.server.request.args = {'cam_url': 'rtsp://camera/live'}
        self.server.Queue.return_value.get.return_value = b'jpeg-data'
        self.server.snapshot()
        self.server.Response.assert_called_once_with(
            b'jpeg-data', mimetype='image/jpeg', status=200,
        )

    def test_both_endpoints_ignore_invalid_auth_params_when_auth_is_disabled(self):
        params = {'cam_url': 'rtsp://camera/live', 'time': 'NaN', 'md5': 'bad'}
        for key in ('', None):
            with self.subTest(private_key=key):
                if key is None:
                    os.environ.pop('PRIVATE_KEY', None)
                else:
                    os.environ['PRIVATE_KEY'] = key
                self.server.process_task.run_task.reset_mock()
                sock = self.make_socket(self.stream_request(params))
                self.server.handle(sock, ('127.0.0.1', 12345))
                self.assertTrue(sock.send.call_args.args[0].startswith(b'HTTP/1.1 200 OK'))
                self.server.process_task.run_task.assert_called_once()

                self.server.request.args = params
                self.server.Queue.return_value.get.return_value = b'jpeg-data'
                self.server.Response.reset_mock()
                self.server.snapshot()
                self.server.Response.assert_called_once_with(
                    b'jpeg-data', mimetype='image/jpeg', status=200,
                )

    def test_snapshot_missing_camera_still_returns_404_when_auth_is_disabled(self):
        self.server.request.args = {}
        self.server.snapshot()
        self.server.Response.assert_called_once_with(b'', mimetype='image/jpeg', status=404)
        self.server.threading.Thread.assert_not_called()


if __name__ == '__main__':
    unittest.main()
