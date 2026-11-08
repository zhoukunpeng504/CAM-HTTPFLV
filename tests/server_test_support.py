"""Shared server fixture; external video and network services use test doubles."""

from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import utils


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.context = ExitStack()
        self.addCleanup(self.context.close)
        self.context.enter_context(patch.dict(os.environ, {'PRIVATE_KEY': ''}))
        # Import the real server without gevent monkey-patching the test runner
        # or loading Flask, Redis, OpenCV, PyAV and the video worker modules.
        names = (
            'gevent', 'gevent.monkey', 'gevent.queue', 'psutil', 'setproctitle',
            'redis', 'flask', 'flask_cors', 'av', 'cv2',
            'utils._av_', 'utils.process_task',
        )
        modules = {name: MagicMock(name=name) for name in names}
        modules['flask'].Flask.return_value.route.side_effect = (
            lambda *args, **kwargs: lambda view: view
        )
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

