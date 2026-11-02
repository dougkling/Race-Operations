"""Fixed loopback adapter; the OpenAI key never enters Race Operations."""
import json
import re
import time
import urllib.request
from pathlib import Path

REASONS = ('healthy','checking','stale','credentials_missing','credentials_unreadable',
           'timeout','connection_failed','authentication_failed','rate_limited','quota_exhausted',
           'provider_error','request_rejected','invalid_response','request_stalled','reconnecting')
BASE = 'http://127.0.0.1:8765/api/ops/'

def call(config, path, data=None):
    token=Path(config['aiMonitorTokenFile']).read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'[a-f0-9]{64}',token):
        raise ValueError('Monitor authorization unavailable')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    request=urllib.request.Request(BASE+path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with opener.open(request,timeout=3) as response:
        return json.loads(response.read(16384))

def sample(config, clock=time.time):
    row={'id':'racebot-ai','status':'unknown','aiReason':'monitor_unavailable'}
    try:
        data=call(config,'ai-health')
        if data.get('schema') != 1 or data.get('status') not in ('green','red','unknown'):
            return row
        stamp=data.get('observedAt')
        if type(stamp) is not int or not -5 <= clock()-stamp <= 30:
            return dict(row,aiReason='stale')
        reason=data.get('reason')
        if reason not in REASONS:
            return row
        # Require real test evidence for green, never a key-configured flag.
        checked=data.get('lastCheckedEpoch')
        if data['status']=='green' and (reason!='healthy' or type(checked) is not int or not -5 <= clock()-checked <= 900):
            return dict(row,aiReason='stale')
        row.update(status=data['status'],aiReason=reason)
        row['lastCheckedEpoch']=checked if type(checked) is int and 0<=checked<=4294967295 else None
        latency=data.get('latencyMs')
        row['latencyMs']=latency if type(latency) is int and 0<=latency<=1000000 else None
        row['aiReconnecting']=data.get('reconnecting') is True
        completed=data.get('completedRequestId')
        row['completedRequestId']=completed if isinstance(completed,str) and re.fullmatch(r'[a-f0-9-]{36}',completed) else None
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        pass
    return row

def reconnect(config, request_id, sleep=time.sleep, clock=time.monotonic):
    if config.get('hostId')!='cloud' or not config.get('aiReconnectEnabled'):
        return 'skipped','agent_controls_disabled'
    current=sample(config)
    if current['status']=='green':return 'skipped','already_healthy'
    if current['status']!='red':return 'skipped','unsafe_preflight'
    try:
        result=call(config,'ai-reconnect',{'requestId':request_id})
        if result.get('requestId')!=request_id:return 'indeterminate','execution_uncertain'
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        return 'indeterminate','execution_uncertain'
    deadline=clock()+155
    while clock()<deadline:
        row=sample(config)
        if row.get('completedRequestId')==request_id:
            return ('succeeded','ai_health_passed') if row['status']=='green' else ('failed','ai_health_failed')
        sleep(2)
    return 'indeterminate','execution_uncertain'
