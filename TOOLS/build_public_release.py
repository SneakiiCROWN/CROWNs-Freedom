"""Package the current CROWN SDK mod without game files or private diagnostics."""
from pathlib import Path
import argparse,re,zipfile,hashlib,json
P=Path(__file__).resolve().parents[1]
def build(output):
 source=(P/'SOURCE/__init__.py').read_bytes();text=source.decode('utf-8-sig')
 name=re.search(r'^ART_MOD_FILENAME\s*=\s*"([^"]+)"',text,re.M).group(1)
 version=re.search(r'^BUILD_ID\s*=\s*"([^"]+)"',text,re.M).group(1)
 output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True);mod=output/name
 assert not mod.exists(),'Use a new output folder; existing builds are preserved'
 root=name.removesuffix('.sdkmod');files={root+'/__init__.py':source,root+'/pyproject.toml':(P/'SOURCE/pyproject.toml').read_bytes()}
 for folder in ['CROWN_CC0_ASSETS','REFERENCE']:
  for p in (P/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:files[root+'/'+p.relative_to(P).as_posix()]=p.read_bytes()
 for name in ['LICENSE.txt','README.md']:files[root+'/'+name]=(P/name).read_bytes()
 with zipfile.ZipFile(mod,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,data in sorted(files.items()):
   info=zipfile.ZipInfo(name,date_time=(2026,10,20,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
 with zipfile.ZipFile(mod) as z:assert z.testzip() is None
 receipt={'build_id':version,'sdkmod':mod.name,'sdkmod_sha256':hashlib.sha256(mod.read_bytes()).hexdigest(),'runtime_source_sha256':hashlib.sha256(source).hexdigest(),'asset_hashes':{n.split('/CROWN_CC0_ASSETS/',1)[1]:hashlib.sha256(d).hexdigest() for n,d in files.items() if '/CROWN_CC0_ASSETS/' in n},'native_gameplay_verified':False}
 (output/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 outer=output/('CROWNs-Freedom-Windows-'+version.split('-')[-1].upper()+'-Test.zip')
 with zipfile.ZipFile(outer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.write(mod,mod.name)
  for name in ['README.md','LICENSE.txt','INSTALL.txt','BUILD_RECEIPT.json']:
   path=output/name if name=='BUILD_RECEIPT.json' else P/name;z.write(path,name)
 (output/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [mod,outer]),encoding='ascii')
 print(outer)
 return outer
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();build(a.output)
