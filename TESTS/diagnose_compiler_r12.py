"""Compile-only bounded control. Never execute compiled modules or import SDKs."""
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
control='\n'.join(f'def independent_{i}(x):\n    values={{"index":{i},"caption":"independent allocation control","limits":(1,2,3,4)}}\n    return [n+x for n in values["limits"] if n>0]\n' for i in range(3000))
cases=[('independent-generated',control),('preserved-R11',(R/'ROLLBACK/STUDIO_UX_R11_SOURCE.py').read_text(encoding='utf-8')),('current-R12',(R/'SOURCE/__init__.py').read_text(encoding='utf-8'))]
results=[]
for name,source in cases:
    before=hashlib.sha256(source.encode()).hexdigest();errors=[]
    print('INPUT',name,len(source),before,flush=True)
    for i in range(100):
        try:code=compile(source,name,'exec');del code
        except Exception as error:
            errors.append(dict(iteration=i,kind=type(error).__name__,detail=str(error),input_unchanged=hashlib.sha256(source.encode()).hexdigest()==before))
        if i%25==0:print('PROGRESS',name,i,flush=True)
    results.append(dict(case=name,compiles=100,sha256=before,errors=errors))
report=dict(python=sys.version,mode='COMPILE ONLY: no generated/CROWN code executed; no SDK imports',results=results,
            historical_host_failures_resolved=False,native_crash_resolved=False)
(R/'REFERENCE/COMPILER_CONTROL_R12.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2));sys.exit(any(row['errors'] for row in results))
