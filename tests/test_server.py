"""Test request handling without connecting to video or network services."""

import unittest

from server_test_support import ServerTestCase


class HandleRequestTests(ServerTestCase):
    def test_parsed_options_are_forwarded_to_video_worker(self):
        for value, auto_encode in (('true', False), ('false', True)):
            with self.subTest(allow_h265=value):
                self.server.process_task.run_task.reset_mock()
                sock = self.make_socket((
                    'GET /?cam_url=rtsp%3A%2F%2Fcamera%2Flive.flv'
                    '&cam_type=rtsp-udp&allow_h265=' + value + ' HTTP/1.1\r\n'
                    'Host: localhost\r\n\r\n'
                ).encode())
                self.server.handle(sock, ('127.0.0.1', 12345))
                self.assertTrue(sock.send.call_args.args[0].startswith(b'HTTP/1.1 200 OK'))
                self.server.process_task.run_task.assert_called_once()
                call = self.server.process_task.run_task.call_args.kwargs
                self.assertEqual(call['args'][0], 'rtsp://camera/live')
                self.assertEqual(call['kwargs'], {
                    'cam_type': 'rtsp-udp',
                    'config_json': {'test': True},
                    'enable_auto_encode': auto_encode,
                })

    def test_invalid_requests_return_404_without_starting_worker(self):
        requests = (
            b'GET / HTTP/1.1\r\n\r\n',
            b'GET /?cam_url= HTTP/1.1\r\n\r\n',
            b'GET /live?cam_url=rtsp://camera/live HTTP/1.1\r\n\r\n',
            b'GET /?cam_url=rtsp://camera/live&cam_type=bad HTTP/1.1\r\n\r\n',
            b'POST /?cam_url=rtsp://camera/live HTTP/1.1\r\n\r\n',
            b'', b'not-an-http-request', b'\xff',
        )
        for request in requests:
            with self.subTest(request=request):
                sock = self.make_socket(request)
                self.server.handle(sock, ('127.0.0.1', 12345))
                sock.send.assert_called_once_with(
                    b'HTTP/1.1 404 Not Found\r\n\r\nNot Found',
                )
        self.server.process_task.run_task.assert_not_called()
        self.server.redis.Redis.from_url.assert_not_called()



if __name__ == '__main__':
    unittest.main()
