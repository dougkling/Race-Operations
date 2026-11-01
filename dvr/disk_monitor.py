"""Read-only capacity of verified local paths; no cleanup or disk operations."""
import shutil
GIB=1024**3

def sample(component_id,recordings=False,usage=shutil.disk_usage):
 row={'id':component_id,'status':'unknown','diskReason':'unavailable','totalBytes':None,'freeBytes':None,'freePercent':None}
 try:
  # C:\\DVR is the operator-confirmed recording path. Query it directly so a
  # missing/inaccessible directory cannot silently fall back to another volume.
  disk=usage('C:\\DVR' if recordings else 'C:\\')
  total,free=disk.total,disk.free
  if type(total) is not int or type(free) is not int or total<=0 or not 0<=free<=total:return row
  percent=100*free/total
  status='red' if free<2*GIB or percent<5 else 'yellow' if free<10*GIB or percent<15 else 'green'
  row.update(status=status,diskReason='critical' if status=='red' else 'low' if status=='yellow' else 'healthy',totalBytes=total,freeBytes=free,freePercent=round(percent,1))
 except (OSError,ValueError):pass
 return row
