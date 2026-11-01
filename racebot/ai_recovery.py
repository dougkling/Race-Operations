"""Explicit, local AI credential reload and access test; never posts chat messages."""
import os
import threading
import time
import uuid


class AIRecovery:
    def __init__(self, hub, verify, load_key, clock=time.time):
        self.hub, self.verify, self.load_key, self.clock = hub, verify, load_key, clock
        self.lock = threading.RLock()
        self.request_id = None
        self.state = 'untested'
        self.result = ''
        self.checked = None
        self.started = None

    def snapshot(self):
        with self.lock:
            return {'protocol': 1, 'configured': bool(self.hub.root.key),
                    'state': self.state, 'result': self.result,
                    'requestId': self.request_id, 'checkedEpoch': self.checked}

    def start(self, request_id):
        try:
            if str(uuid.UUID(request_id)) != request_id:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ValueError('A valid request ID is required.') from None
        with self.lock:
            if request_id == self.request_id:
                return self.snapshot()
            if self.state == 'running' or (self.started is not None and self.clock()-self.started < 120):
                raise ValueError('AI reconnect is running or cooling down.')
            self.request_id, self.state, self.result = request_id, 'running', ''
            self.started = self.clock()
            threading.Thread(target=self._run, daemon=True).start()
            return self.snapshot()

    def _run(self):
        state, result = 'failed', 'ai_access_failed'
        try:
            with self.hub.lock:
                previous_key = self.hub.root.key
                model = self.hub.root.config['model']
            key = os.environ.get('OPENAI_API_KEY') or self.load_key()
            if not key:
                result = 'ai_key_missing'
            else:
                # One bounded test, no chat content, web tools or automatic retries.
                response = self.verify(key, model)
                if not isinstance(response, dict) or not response.get('id') or response.get('object') != 'response' or response.get('error'):
                    raise ValueError('AI test did not return a response.')
                with self.hub.lock:
                    if self.hub.root.key != previous_key or self.hub.root.config['model'] != model:
                        result = 'ai_configuration_changed'
                    else:
                        for engine in self.hub._all_engines():
                            with engine.lock:
                                engine.key = key
                        state, result = 'verified', 'ai_access_verified'
        except Exception:
            # Provider errors may include credentials or user data; expose only a fixed result.
            pass
        with self.lock:
            self.state, self.result, self.checked = state, result, int(self.clock())
