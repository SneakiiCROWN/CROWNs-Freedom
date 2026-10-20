import ast, sys, types, time
from pathlib import Path
from types import SimpleNamespace
src=(Path(__file__).resolve().parent.parent/'SOURCE'/'__init__.py').read_text()
ast.parse(src)

class W:
 def __init__(self, name=''):self.name=name;self.children=[];self.WidgetTree=None;self.slot=None;self.value=.9;self.pressed=False
 def AddChild(self,w):self.children.append(w);w.slot=W('slot')
 def __getattr__(self,key):
  if key.startswith(('Set','Remove','Add','Force','Clear','Reset')):return lambda *a:None
  raise AttributeError(key)
 def IsPressed(self):return self.pressed
 def GetValue(self):return self.value
class P:
 def __init__(self):
  self.addr=id(self);self.bCanBeDamaged=True;self.bActorEnableCollision=True
  self.OakCharacterMovement=SimpleNamespace(MovementMode=1,SetMovementMode=lambda *a:None,
        MinAnalogWalkSpeed=600.,MaxWalkSpeed=600.,JumpZVelocity=840.,GravityScale=1.)
 def _get_address(self):return self.addr
 def K2_GetActorLocation(self):return SimpleNamespace(X=1000.,Y=2000.,Z=200.)
 def K2_GetActorRotation(self):return SimpleNamespace(Yaw=90.)
 def K2_GetActorTransform(self):return SimpleNamespace(Translation=None)
 def HasAuthority(self):return True
class PC:
 def __init__(self):
  self.OakCharacter=pawn;self.Pawn=pawn;self.PlayerState=ps
  self.player=SimpleNamespace(BaseFOV=100,VehicleFOV=100)
  self.bShowMouseCursor=False;self.bEnableMouseOverEvents=False;self.bEnableClickEvents=False;self.bEnableTouchEvents=False;self.bBlockInput=False
 def HasAuthority(self):return True
 def IsInputKeyDown(self,*a):return False
 def _get_address(self):return id(self)
class Pool:
 def __init__(self):self.calls=[]
 def SpawnInventoryFromItemPool(self,world,transform,level,name):
  self.calls.append((world,transform.Translation,level,name))
pawn=P();ps=SimpleNamespace(_get_address=lambda:id(ps));pc=PC();pool=Pool();mode=[0]
world=SimpleNamespace(GameState=SimpleNamespace(PlayerArray=[ps]),GetNetMode=lambda:mode[0],GetName=lambda:'WhistlersMaw', TimeDilation=1.,PersistentLevel=None)
world.PersistentLevel=SimpleNamespace(WorldSettings=world)
ENGINE=SimpleNamespace(GameViewport=SimpleNamespace(World=world))
mods=types.ModuleType('mods_base');mods.get_pc=lambda **kw:pc;mods.build_mod=lambda **kw:None;mods.keybind=lambda *a,**kw:lambda fn:fn;mods.ENGINE=ENGINE
hooks=types.ModuleType('unrealsdk.hooks');hooks.Type=SimpleNamespace(POST='POST');hooks.add_hook=lambda *a:None;hooks.remove_hook=lambda *a:None
unreal=types.ModuleType('unrealsdk.unreal');unreal.IGNORE_STRUCT=object()
u=types.ModuleType('unrealsdk');u.logging=SimpleNamespace(info=lambda *a:None)
u.make_struct=lambda typ,**kw:SimpleNamespace(**kw)
u.find_all=lambda name,exact: [pool] if name=='NexusConfigStoreItemPool' else []
u.find_class=lambda name:SimpleNamespace(ClassDefaultObject=SimpleNamespace(RefillCooldown=lambda *a:None,LockTargetableByAI=lambda *a:None))
u.find_object=lambda kind,path:SimpleNamespace(ClassDefaultObject=SimpleNamespace(GetViewportScale=lambda pc:1.,GetViewportSize=lambda pc:SimpleNamespace(X=1920.,Y=1080.),SetInputMode_UIOnlyEx=lambda *a:None,SetInputMode_GameAndUIEx=lambda *a:None,SetInputMode_GameOnly=lambda *a:None))
u.construct_object=lambda cls,outer:W(str(cls))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
# Importing this fixture must not re-run its complete regression program.
if __name__=='__main__':
 try:
  sys.modules.update({'mods_base':mods,'unrealsdk':u,'unrealsdk.hooks':hooks,'unrealsdk.unreal':unreal})
  ns={};exec(compile(src,'test_crown_v12','exec'),ns)
  state=ns['State'];ns['open_menu']();assert state.opened
  assert ns['spawn_probe']()
  assert not ns['spawn_request']() and not pool.calls
  assert ns['spawn_request']() and len(pool.calls)==1
  _,vec,level,poolname=pool.calls[0]
  assert level==40 and 'convergence' in poolname.lower() and abs(vec.Y-2220)<.001,(vec.X,vec.Y)
  state.anti_spam_until=0
  ns['toggle_spawn_count']();assert state.spawn_count==2
  assert not ns['spawn_request']() and len(pool.calls)==1
  assert ns['spawn_request']() and len(pool.calls)==3
  mode[0]=3
  assert not ns['spawn_request']() and len(pool.calls)==3
  assert not ns['spawn_probe']()
  mode[0]=0
  state.spawn_pending=None
  assert not ns['spawn_request']()
  world.GetName=lambda:'OtherMap'
  assert not ns['spawn_request']() and len(pool.calls)==3
  world.GetName=lambda:'WhistlersMaw'
  state.spawn_pending=None
  ns['toggle_nav_group']();assert state.page=='SPAWN'
  ns['show_page']('EVENTS')
  assert ns['start_event']('BULLET BALLET') and world.TimeDilation==.5
  assert ns['start_event']('MOON BOOTS') and pawn.OakCharacterMovement.GravityScale==.5
  ns['stop_event']();assert world.TimeDilation==1 and pawn.OakCharacterMovement.GravityScale==1
  mode[0]=3
  assert not ns['start_event']('HYPERDRIVE')
  mode[0]=0
  features=ns['feature_probe']();assert features['ITEM POOLS'] is True
  # v1.3 curated category browser: all unique tokens and safe selections.
  pools=ns['SPAWN_POOLS']
  assert len(pools)>=50,len(pools)
  assert len({row[1].lower() for row in pools})==len(pools),'Duplicate item-pool token'
  assert set(row[2] for row in pools)==set(ns['SPAWN_CATEGORIES'][1:6])
  assert ns['_spawn_category']()=='ALL'
  assert len(ns['_spawn_visible_indices']())==len(pools)
  for category_idx in range(1,6):
   ns['cycle_spawn_category']()
   assert state.spawn_category_idx==category_idx
   first=state.spawn_pool_idx
   assert pools[first][2]==ns['_spawn_category']()
   seen=set()
   for j in range(len(ns['_spawn_visible_indices']())):
    assert pools[state.spawn_pool_idx][2]==ns['_spawn_category']()
    seen.add(state.spawn_pool_idx)
    ns['cycle_spawn_pool']()
   assert len(seen)==len(ns['_spawn_visible_indices']())
   assert state.spawn_pool_idx==first
   ns['cycle_spawn_pool'](-1)
   assert state.spawn_pool_idx in seen
  # v1.4 saved favorites and recent requests are categories, not game content.
  # Enter Favorites (empty initially), make sure no item is implicitly spawned.
  ns['cycle_spawn_category'](); assert ns['_spawn_category']()=='FAVORITES'
  assert ns['_spawn_visible_indices']()==[]
  assert not ns['spawn_request']()
  # Adding a favorite is only allowed for a visible selected item.
  assert not ns['toggle_spawn_favorite']()
  ns['cycle_spawn_category'](); assert ns['_spawn_category']()=='RECENT'
  assert len(ns['_spawn_visible_indices']())>=1
  assert ns['_forge_selection']() is not None
  # Recent requests are labelled only as attempted native calls.
  ns['cycle_spawn_category'](); assert ns['_spawn_category']()=='ALL'
  assert ns['toggle_spawn_favorite']()
  token=ns['SPAWN_POOLS'][state.spawn_pool_idx][1]
  assert token in state.spawn_favorites
  ns['cycle_spawn_category']()
  for _ in range(5):ns['cycle_spawn_category']()
  assert ns['_spawn_category']()=='FAVORITES'
  assert ns['_spawn_visible_indices']()
  assert state.spawn_pool_idx in ns['_spawn_visible_indices']()
  assert ns['toggle_spawn_favorite']()
  assert token not in state.spawn_favorites
  assert ns['_spawn_visible_indices']()==[]
  assert not ns['spawn_request']()
  # Category cycle returns ALL and every entry remains selectable.
  ns['cycle_spawn_category'](); assert ns['_spawn_category']()=='RECENT'
  ns['cycle_spawn_category']()
  assert state.spawn_category_idx==0
  ns['reset_spawn_settings']()
  assert state.spawn_pool_idx==0 and state.spawn_category_idx==0
  assert not ns['spawn_request']() and state.spawn_pending is not None
  ns['cycle_spawn_category']()
  assert state.spawn_pending is None and state.spawn_expires==0
  # Cannot report an event active after failing to apply gravity.
  mode[0]=0
  prior_gravity=pawn.OakCharacterMovement.GravityScale
  pawn.OakCharacterMovement.GravityScale=object()
  assert not ns['start_event']('MOON BOOTS')
  assert state.active_event=='NONE' and world.TimeDilation==1.0
  pawn.OakCharacterMovement.GravityScale=prior_gravity
  assert ns['start_event']('LOW GRAV DASH')
  assert world.TimeDilation==1.0 and pawn.OakCharacterMovement.GravityScale==.5
  assert state.motion_scale==2.0
  ns['stop_event']()
  assert world.TimeDilation==1.0 and pawn.OakCharacterMovement.GravityScale==1.0
  assert pawn.OakCharacterMovement.MinAnalogWalkSpeed==600.0
  assert ns['start_event']('BULLET TIME RUN') and world.TimeDilation==.5
  ns['stop_event']()
  assert state.motion_scale==1.0 and world.TimeDilation==1.0
  ns['reset_ui_defaults']();assert 1.0<=state.font_scale<=1.1 and .9<=state.panel_opacity<=1.0
  for res in ((2560,1440),(1920,1080),(1280,720),(854,480)):
   ns['viewport']=lambda res=res:res
   for tab in ('PLAYER','MOTION','COMBAT','LOOT','WORLD','PARTY','SPAWN','EVENTS','CONTENT','PRESETS','STYLE','DEV'):
    ns['show_page'](tab)
    assert state.draw_ok, (res,tab,state.message)
    assert len(state.buttons)>=6, (res,tab)
  ns['close_menu']();assert not state.opened
  print('PASS: spawn two-click/cap/authority/map, event presets/restore, feature probe, 12 pages x 4 resolutions')
 finally:
  for k,v in old.items():
   if v is None:sys.modules.pop(k,None)
   else:sys.modules[k]=v
