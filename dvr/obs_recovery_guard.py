"""Fail closed unless OBS is absent or authenticated recording and streaming states are idle."""
import sys
from dvr_control import inventory
from obs_monitor import Reader

def safe():
 count=inventory().get('obsProcessCount')
 if count==0:return True
 if count!=1:return False
 reader=Reader()
 try:
  status=reader.probe()
  if status.get('recording') is not False or status.get('obsConnected') is not True:return False
  # Stopping OBS also affects a stream. Keep that check local to recovery.
  reader.ws.send({'op':6,'d':{'requestType':'GetStreamStatus','requestId':'raceops-stream-guard'}})
  response=reader.ws.receive();d=response.get('d',{})
  return response.get('op')==7 and d.get('requestId')=='raceops-stream-guard' and d.get('requestType')=='GetStreamStatus' and d.get('requestStatus',{}).get('result') is True and d.get('responseData',{}).get('outputActive') is False
 except Exception:return False
 finally:reader.close()

if __name__=='__main__':sys.exit(0 if safe() else 1)
