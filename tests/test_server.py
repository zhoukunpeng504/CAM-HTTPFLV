"""Check handler wiring while replacing external services with test doubles."""

from contextlib import ExitStack
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import utils


class HandleRequestTests(unittest.TestCase):
    def setUp(self):
        self.context = ExitStack()
        self.addCleanup(self.context.close)
        # Import the real server without gevent monkey-patching the test runner
        # or loading Flask, Redis, OpenCV, PyAV and the video worker modules.
        names = (
            'gevent', 'gevent.monkey', 'gevent.queue', 'psutil', 'setproctitle',
            'redis', 'flask', 'flask_cors', 'av', 'cv2',
            'utils._av_', 'utils.process_task',
        )
        modules = {name: MagicMock(name=name) for name in names}
        self.context.enter_context(patch.dict('sys.modules', modules))
        self.context.enter_context(patch.object(utils, '_av_', modules['utils._av_'], create=True))
        self.context.enter_context(patch.object(
            utils, 'process_task', modules['utils.process_task'], create=True,
        ))
        source = Path(__file__).resolve().parents[1] / 'server.py'
        spec = importlib.util.spec_from_file_location('server_under_test', source)
        self.server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.server)
        self.server.CONFIG_JSON = {'test': True}
        self.server.redis_url = 'redis://unused/0'
        self.server.process_task.run_task.return_value = 'test-task'
        self.context.enter_context(patch.object(self.server, 'print_to_logger'))
        # Do not inspect real worker PID files during handler cleanup.
        self.context.enter_context(patch('builtins.open', side_effect=FileNotFoundError))

    def make_socket(self, request):
        sock = MagicMock()
        sock.recv.return_value = request
        sock.closed = True  # Exit the streaming loop immediately.
        return sock

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
