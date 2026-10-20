"""Black Market Premier: transactional gameplay, semantic status & safe visual geometry.
Mocks only, NEVER a replacement for an actual Borderlands 4 acceptance test.
"""
from pathlib import Path
from types import SimpleNamespace
import sys,runpy,json,tempfile
root=Path(__file__).resolve().parents[1]
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal')}
try:
 sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
     'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
 ns={'__name__':'crowns_premier_test'}
 exec(compile((root/'SOURCE/__init__.py').read_text(),'crown_v30','exec'),ns)
 state=ns['State'];actor=ctx['pawn'];pc=ctx['pc'];ctx['mode'][0]=0
 # Status messages never overflow, even if SetText is updated without redraw.
 updated=[];tag=[]
 state.status_widget=SimpleNamespace(SetText=lambda v:updated.append(str(v)))
 state.status_label=SimpleNamespace(SetText=lambda v:tag.append(str(v)))
 state.status_chars=49
 for msg,kind in (
    ('SPAWN FAILED // API unavailable','ERROR'),
    ('CONFIRM SPAWN // press again to request','CAUTION'),
    ('WORLD TIME x4.00 (readback OK)','OK'),
    ('Roster updated','INFO'),
 ):
    ns['log'](msg)
    assert state.status_kind==kind,(msg,state.status_kind)
    assert updated and len(updated[-1])<=49,(msg,updated[-1])
    assert tag[-1]==ns['_status_caption'](),(kind,tag[-1])
 state.status_widget=state.status_label=None
 # Failed second write cannot leave MinAnalogWalkSpeed modified.
 class FragileMove:
    def __init__(self):
      self.MinAnalogWalkSpeed=600.; self._max=600.; self.JumpZVelocity=840.;self.GravityScale=1.
    @property
    def MaxWalkSpeed(self):return self._max
    @MaxWalkSpeed.setter
    def MaxWalkSpeed(self,v):
      if v!=600.:raise RuntimeError('reflected property is readonly on patch')
      self._max=v
 broken=FragileMove()
 original_move=actor.OakCharacterMovement
 actor.OakCharacterMovement=broken
 state.motion_owner=None;state.motion_originals={}
 assert ns['tune_motion']('speed',2.) is False
 assert broken.MinAnalogWalkSpeed==600 and broken.MaxWalkSpeed==600
 assert state.motion_scale==1.0 and not state.motion_originals
 actor.OakCharacterMovement=original_move
 assert ns['tune_motion']('speed',1.5)
 assert abs(state.motion_scale-1.5)<.01
 assert ns['tune_motion']('jump',2.0)
 assert state.jump_selected==2.0
 assert ns['tune_motion']('gravity',.5)
 assert state.gravity_selected==.5
 ns['restore_motion']()
 assert (state.motion_scale,state.jump_selected,state.gravity_selected)==(1.,1.,1.)
 # FOV currently written values are highlighted only AFTER verified readback.
 ns['change_fov'](115)
 assert state.fov_selected==115
 ns['reset_fov']()
 assert state.fov_selected is None
 # Render geometry captured from the actual drawing code at 4 resolutions.
 orig_btn=ns['btn']; orig_note=ns['note_panel']; orig_chip=ns['chip']
 trace={'buttons':[],'notes':[],'chips':[]}
 def watch_btn(parent,label,x,y,w,h,fn,*args,**kwargs):
    trace['buttons'].append((str(label),float(x),float(y),float(w),float(h),bool(kwargs.get('disabled',False))))
    return orig_btn(parent,label,x,y,w,h,fn,*args,**kwargs)
 def watch_note(parent,title,body,x,y,w,h,*args,**kwargs):
    trace['notes'].append((str(title),float(x),float(y),float(w),float(h)))
    return orig_note(parent,title,body,x,y,w,h,*args,**kwargs)
 def watch_chip(parent,label,*args,**kwargs):
    trace['chips'].append(str(label))
    return orig_chip(parent,label,*args,**kwargs)
 ns['btn']=watch_btn;ns['note_panel']=watch_note;ns['chip']=watch_chip
 sizes=((2560,1440),(1920,1080),(1280,720),(854,480))
 pages=tuple(ns['PAGE_HELP'])
 for res in sizes:
    ns['viewport']=lambda x=res:x
    ns['open_menu']()
    assert state.opened and state.draw_ok,res
    for page in pages:
      state.help_open=False;state.expand_theme=False;state.style_audio_open=False
      state.spawn_view='BROWSE';state.diag_open=False;state.activity_open=False
      trace['buttons'].clear();trace['notes'].clear();trace['chips'].clear()
      ns['show_page'](page)
      assert state.draw_ok,(res,page)
      x,y,w,h,*_=state.panel_rect
      foot=y+h-141
      main_start=x+201 # extra conservative: main pane starts around sidebar + 18
      # Every actionable control must stay in the panel; page buttons stop above footer.
      for label,bx,by,bw,bh,disabled in trace['buttons']:
        assert bx>=x+10 and bx+bw<=x+w-8,(res,page,'button horizontal',label)
        assert by>=y+16 and by+bh<=y+h-18,(res,page,'button vertical',label)
        if (bx>=main_start and by>=y+214 and by<foot):
            assert by+bh<=foot-2,(res,page,'button crosses quick bar',label)
      for title,nx,ny,nw,nh in trace['notes']:
        assert ny+nh<foot-1,(res,page,'note crosses footer',title)
        for label,bx,by,bw,bh,disabled in trace['buttons']:
          if bx>=main_start and by>=y+210 and by<foot:
            overlap=(nx<bx+bw-2 and bx<nx+nw-2 and ny<by+bh-2 and by<ny+nh-2)
            assert not overlap,(res,page,'note/button intersection',title,label)
      # More complicated subviews must also fit.
      variants=[]
      if page=='STYLE':variants=['audio','themes']
      if page=='DEV':variants=['diag','activity']
      if page=='SPAWN':variants=['search','level','tools']
      variants+=['help']
      for v in variants:
        state.help_open=v=='help'
        state.expand_theme=v=='themes'
        state.style_audio_open=v=='audio'
        state.diag_open=v=='diag'
        state.activity_open=v=='activity'
        state.spawn_view={'search':'SEARCH','level':'LEVEL','tools':'TOOLS'}.get(v,'BROWSE')
        trace['buttons'].clear();trace['notes'].clear()
        ns['redraw']()
        assert state.draw_ok,(res,page,v)
        foot=state.panel_rect[1]+state.panel_rect[3]-141
        xx,yy,ww,hh,*_=state.panel_rect
        for label,bx,by,bw,bh,disabled in trace['buttons']:
          assert bx>=xx+10 and bx+bw<=xx+ww-8,(res,page,v,'button horizontal',label)
          assert by>=yy+16 and by+bh<=yy+hh-18,(res,page,v,'button vertical',label)
          if bx>=xx+201 and by>=yy+214 and by<foot:
             assert by+bh<=foot-2,(res,page,v,'button footer',label,by+bh,foot)
        for title,nx,ny,nw,nh in trace['notes']:
          assert ny+nh<=foot-2,(res,page,v,'note footer',title)
          for label,bx,by,bw,bh,disabled in trace['buttons']:
            if bx>=xx+201 and by>=yy+210 and by<foot:
              overlap=(nx<bx+bw-2 and bx<nx+nw-2 and ny<by+bh-2 and by<ny+nh-2)
              assert not overlap,(res,page,v,'note/button overlap',title,label)
    ns['close_menu']()
 # Client role: actions shown but safely disabled until host/consent established.
 state.party_approved=False;state.party=[];ctx['mode'][0]=0
 ns['viewport']=lambda:(1920,1080)
 ns['open_menu']();trace['buttons'].clear();ns['show_page']('PARTY')
 remote=[x for x in trace['buttons'] if x[0] in ('TOGGLE FRIEND GOD MODE','REFILL FRIEND SKILL')]
 assert len(remote)==2 and all(x[5] for x in remote)
 # Export report is privacy conscious and contains no player names.
 with tempfile.TemporaryDirectory() as folder:
    ns['SETTINGS_DIR']=Path(folder)
    assert ns['export_qa_report']()
    report=json.loads((Path(folder)/'CROWNs_Freedom_QA_Report.json').read_text())
    assert report['version']=='5.26.0' and report['ui']['message_kind']
    assert set(report['effects'])>=set(('world_time_multiplier','jump_multiplier','gravity_multiplier','fov_selected'))
 ns['close_menu']()
 print('PASS v3.0: transactional motion rollback, selected FOV/jump/gravity, semantic status, 12 pages + subviews at four viewports, report privacy')
finally:
 for name,item in old.items():
  if item is None:sys.modules.pop(name,None)
  else:sys.modules[name]=item
