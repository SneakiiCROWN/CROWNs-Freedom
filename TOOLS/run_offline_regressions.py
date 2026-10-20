"""Run synthetic SDK tests without reading the user's physical keyboard/focus.

Historical fixtures assume non-Windows fallback input. Each isolated child
simulates that platform branch. Tests of Win32/XInput explicitly switch to
win32 and provide their own fake native packets. Production code is untouched.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys, subprocess, os, time, json, hashlib

ROOT=Path(__file__).resolve().parents[1]
def run(path):
    driver="import runpy,sys,os; sys.platform='linux'; \
trace=lambda *a:trace;sys.settrace(trace if os.environ.get('CROWN_TRACE_PYTHON')=='1' else None); \
runpy.run_path(sys.argv[1],run_name='__main__')"
    started=time.monotonic()
    try:
        r=subprocess.run([sys.executable,'-X','utf8','-c',driver,str(path)],cwd=ROOT,
            capture_output=True,text=True,encoding='utf-8',timeout=60,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1'))
        return dict(test=path.name,passed=r.returncode==0,exit_code=r.returncode,
                    seconds=round(time.monotonic()-started,2),detail=(r.stdout+'\n'+r.stderr)[-1800:])
    except subprocess.TimeoutExpired:return dict(test=path.name,passed=False,detail='60 second timeout')
if __name__=='__main__':
    tests=[ROOT/'TESTS'/x for x in sys.argv[1:]] if sys.argv[1:] else sorted((ROOT/'TESTS').glob('test*.py'))
    results=[];started=time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        for future in as_completed([pool.submit(run,p) for p in tests]):
            result=future.result();results.append(result)
            if not result['passed']:print('FAIL',result['test'],result['detail'][-600:],flush=True)
    report=dict(source_sha256=hashlib.sha256((ROOT/'SOURCE/__init__.py').read_bytes()).hexdigest(),
        python_version=sys.version,python_trace=os.environ.get('CROWN_TRACE_PYTHON')=='1',total=len(tests),passed=sum(x['passed'] for x in results),seconds=round(time.monotonic()-started,2),
        mode='Synthetic SDK; non-native input fallback simulated; no BL4/physical controller verification',
        results=sorted(results,key=lambda x:x['test']))
    (ROOT/'QA_CURRENT_OFFLINE.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('RESULT',report['passed'],'/',report['total'],flush=True)
    sys.exit(report['passed']!=report['total'])
