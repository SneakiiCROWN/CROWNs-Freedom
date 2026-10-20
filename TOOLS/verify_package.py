"""Check the actual release archives and start their module with a synthetic SDK."""
from pathlib import Path
import argparse,zipfile,hashlib,json,re,runpy,sys,importlib
P=Path(__file__).resolve().parents[1]
def verify(folder):
 folder=Path(folder).resolve();receipt=json.loads((folder/'BUILD_RECEIPT.json').read_text());outer=next(folder.glob('CROWNs-Freedom-Windows-*.zip'));mod=folder/receipt['sdkmod']
 with zipfile.ZipFile(outer) as z:
  assert z.testzip() is None
  assert z.read(mod.name)==mod.read_bytes(),'ZIP does not contain the tested SDK mod'
 expected=json.loads((P/'VERIFIED_LOCAL_CHECKPOINT.json').read_text())
 root=mod.stem
 with zipfile.ZipFile(mod) as z:
  assert z.testzip() is None
  source=z.read(root+'/__init__.py');assert hashlib.sha256(source).hexdigest()==receipt['runtime_source_sha256']
  assert source==(P/'SOURCE/__init__.py').read_bytes()
  assets={n.split('/CROWN_CC0_ASSETS/',1)[1]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if '/CROWN_CC0_ASSETS/' in n}
  assert assets==receipt['asset_hashes']
  if receipt['build_id']=='5.26.0-echo-fieldcraft-r22':
   assert receipt['runtime_source_sha256']==expected['runtime_source_sha256']
   assert {'CROWN_CC0_ASSETS/'+k:v for k,v in assets.items()}==expected['assets']
  for n in z.namelist():
   assert not re.search(r'(?i)(?:\.(?:exe|dll|sav|pfx|keystore)$|HOST_APPLICATION_FAULTS|USER_.*DIRECTIVE|UPSTREAM_SOURCE|UPLOAD_INVENTORY)',n),n
 # Execute the packaged module through zipimport, never the source checkout.
 fixture=runpy.run_path(str(P/'TESTS/test_arsenal_events.py'))
 old={n:sys.modules.get(n) for n in ['mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal']};platform=sys.platform
 try:
  sys.platform='linux';sys.modules.update({'mods_base':fixture['mods'],'unrealsdk':fixture['u'],'unrealsdk.hooks':fixture['hooks'],'unrealsdk.unreal':fixture['unreal']});sys.path.insert(0,str(mod))
  runtime=importlib.import_module(root)
  assert runtime.BUILD_ID==receipt['build_id'];runtime.open_menu();assert runtime.State.opened
  pages=('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV')
  for res in ((2560,1440),(1920,1080),(1280,720),(854,480)):
   runtime.viewport=lambda res=res:res
   for page in pages:
    runtime.show_page(page);assert runtime.State.draw_ok,(res,page)
  runtime.close_menu();assert not runtime.State.opened
 finally:
  sys.platform=platform
  if str(mod) in sys.path:sys.path.remove(str(mod))
  sys.modules.pop(root,None)
  for n,v in old.items():
   if v is None:sys.modules.pop(n,None)
   else:sys.modules[n]=v
 report={'zip_crc':True,'sdkmod_crc':True,'packaged_zipimport':True,'mocked_menu_start_close':True,'mocked_page_resolution_pairs':48,'source_hash_matches_local_checkpoint':True,'all_asset_hashes_match':True,'native_gameplay_tested':False,'zip_sha256':hashlib.sha256(outer.read_bytes()).hexdigest(),'sdkmod_sha256':hashlib.sha256(mod.read_bytes()).hexdigest()}
 (folder/'PACKAGE_CHECKS.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',required=True);a=p.parse_args();verify(a.folder)
