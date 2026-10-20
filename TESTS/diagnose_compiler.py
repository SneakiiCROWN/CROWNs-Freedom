"""Compile-only probe: no SDK import or execution of any CROWN function."""
from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parents[1]
for name,path in (('R8',root/'ROLLBACK/RECONCILED_R8_SOURCE.py'),('R9',root/'SOURCE/__init__.py')):
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();text=raw.decode('utf-8')
    print('FIXED INPUT',name,len(raw),sha,flush=True)
    for i in range(200):
        try:code=compile(text,'fixed_'+name,'exec')
        except BaseException:
            print('FAILED COMPILE',name,i,'INPUT STILL IDENTICAL',hashlib.sha256(text.encode()).hexdigest()==sha,flush=True)
            raise
        del code
        if i%25==0:print('COMPILE',name,i,flush=True)
print('COMPILE ONLY COMPLETE',sys.version,flush=True)
