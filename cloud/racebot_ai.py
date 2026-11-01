"""Allowlisted loopback-only RaceBot AI recovery protocol."""
import json
import time
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:8765'
ACTION = 'racebot-ai-restart'
LABEL = 'Restart RaceBot AI connection'
STATES = ('untested', 'running', 'verified', 'failed')
RESULTS = ('ai_access_verified', 'ai_access_failed', 'ai_key_missing', 'ai_configuration_changed')


def request(path, payload=None, token=None):
    if path not in ('/api/ops/ai', '/api/ops/ai/reconnect'):
        raise ValueError('Unsupported AI operation')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-PitWall-Token'] = token
    req = urllib.request.Request(BASE+path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    with opener.open(req, timeout=5) as response:
        raw = response.read(16385)
        if len(raw) > 16384:
            raise ValueError('Oversized AI response')
        data = json.loads(raw)
        if not isinstance(data, dict) or data.get('protocol') != 1:
            raise ValueError('Unsupported AI protocol')
        return data


def evidence(call=request):
    try:
        data = call('/api/ops/ai')
        return {'aiRecoverySupported': True, 'aiConfigured': data.get('configured') is True,
                'aiState': data.get('state') if data.get('state') in STATES else 'unknown',
                'aiCheckedEpoch': data.get('checkedEpoch') if type(data.get('checkedEpoch')) is int else None}
    except (OSError, ValueError):
        return {'aiRecoverySupported': False, 'aiState': 'unavailable'}


def perform_restart(config, request_id, call=request, sleep=time.sleep, clock=time.monotonic):
    if config.get('hostId') != 'cloud' or config.get('racebotAiRestartEnabled') is not True:
        return 'skipped', 'agent_controls_disabled'
    profile = next((c for c in config.get('components', []) if c.get('id') == 'racebot'), {})
    if not profile.get('enabled') or profile.get('probe') != 'http' or profile.get('url', '').rstrip('/') != BASE:
        return 'skipped', 'unsafe_preflight'
    try:
        before = call('/api/ops/ai')
        token = before.get('token')
        if before.get('protocol') != 1 or not isinstance(token, str) or not 16 <= len(token) <= 128 or before.get('state') == 'running':
            return 'skipped', 'unsafe_preflight'
    except (OSError, ValueError):
        return 'skipped', 'unsafe_preflight'
    try:
        call('/api/ops/ai/reconnect', {'requestId': request_id}, token)
    except urllib.error.HTTPError:
        return 'failed', 'ai_request_rejected'
    except (OSError, ValueError):
        return 'indeterminate', 'execution_uncertain'
    deadline = clock()+90
    while clock() < deadline:
        try:
            current = call('/api/ops/ai')
            if current.get('requestId') != request_id:
                return 'indeterminate', 'execution_uncertain'
            if current.get('state') == 'verified' and current.get('result') == 'ai_access_verified':
                return 'succeeded', 'ai_access_verified'
            if current.get('state') == 'failed':
                return 'failed', current.get('result') if current.get('result') in RESULTS else 'ai_access_failed'
        except (OSError, ValueError):
            pass
        sleep(2)
    return 'indeterminate', 'execution_uncertain'
