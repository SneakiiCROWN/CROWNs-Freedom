"""Bounded compiler experiment, never executing compiled code or importing SDKs."""
from pathlib import Path
import hashlib,json,sys
R=Path(__file__).resolve().parents[1]
control='\n'.join(f'def independent_probe_{i}(x):\n    values={{"index":{i},"caption":"independent compiler allocation probe","limits":(1,2,3,4)}}\n    return [n+x for n in values["limits"] if n>0]\n' for i in range(3000))
cases=[('generated-control',control),('preserved-R9',(R/'ROLLBACK/STABILISATION_R9_SOURCE.py').read_text(encoding='utf-8')),('current-R10',(R/'SOURCE/__init__.py').read_text(encoding='utf-8'))]
results=[]
for name,source in cases:
    before=hashlib.sha256(source.encode()).hexdigest();errors=[]
    print('FIXED INPUT',name,len(source),before,flush=True)
    for i in range(100):
        try:code=compile(source,name,'exec');del code
        except Exception as error:
            record=dict(iteration=i,kind=type(error).__name__,detail=str(error),input_hash_unchanged=hashlib.sha256(source.encode()).hexdigest()==before)
            errors.append(record);print('COMPILE FAILURE',json.dumps(record),flush=True)
        if i%25==0:print('PROGRESS',name,i,flush=True)
    results.append(dict(case=name,compiles=100,sha256=before,failures=errors))
report=dict(python=sys.version,mode='Compile only; neither generated nor CROWN code executed; no SDK imports',results=results)
(R/'REFERENCE/COMPILER_CONTROL_R10.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
sys.exit(any(row['failures'] for row in results))
