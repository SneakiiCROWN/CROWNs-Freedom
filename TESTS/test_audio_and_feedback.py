"""CROWN v2.2 sound/cache/settings/UI tests. Mocks do NOT verify actual Windows playback in BL4."""
import runpy,sys,tempfile,zipfile,hashlib
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from archive_fixture import identity
ctx=runpy.run_path(str(root/'TESTS/test_arsenal_events.py'))
old={k:sys.modules.get(k) for k in ('mods_base','unrealsdk','unrealsdk.hooks','unrealsdk.unreal','winsound')}
try:
    sys.modules.update({'mods_base':ctx['mods'],'unrealsdk':ctx['u'],
      'unrealsdk.hooks':ctx['hooks'],'unrealsdk.unreal':ctx['unreal']})
    played=[]
    sound=SimpleNamespace(SND_FILENAME=0x20000,SND_ASYNC=1,SND_NODEFAULT=2,
      PlaySound=lambda path, flags:played.append((path,flags)))
    sys.modules['winsound']=sound
    ns={'__name__':'crown_audio_test'}
    source=(root/'SOURCE/__init__.py').read_text(encoding='utf-8')
    exec(compile(source,'crown_audio.py','exec'),ns)
    st=ns['State'];st.sfx_set='CLASSIC'
    assert len(ns['SOUND_HASHES'])==42
    for mode in ('LOW','NORMAL','HIGH'):
        for cue in ns['SOUND_CUES']:
            name=mode.lower()+'_'+cue+'.wav'
            raw=(root/'CROWN_CC0_ASSETS'/'UI_WAV'/name).read_bytes()
            assert ns['_sound_bytes_valid'](name,raw)
            assert not ns['_sound_bytes_valid'](name,raw+b'tamper')
    with tempfile.TemporaryDirectory() as temp:
        base=Path(temp)
        settings=base/'settings';settings.mkdir()
        ns['SETTINGS_DIR']=settings
        archive=base/ns['ART_MOD_FILENAME']
        good=(root/'CROWN_CC0_ASSETS/UI_WAV/low_select.wav').read_bytes()
        def make_archive(data):
            with zipfile.ZipFile(archive,'w') as z:
                identity(z,ns)
                z.writestr('CROWNs_Freedom_v2_2_Audio_and_Feedback/CROWN_CC0_ASSETS/UI_WAV/low_select.wav',data)
        make_archive(good)
        # Missing sound file returns false and doesn't play.
        assert ns['_sound_file']('hover','LOW') is None
        assert ns['_sound_file']('garbage','LOW') is None
        assert ns['_sound_file']('select','OFF') is None
        path=ns['_sound_file']('select','LOW')
        assert path is not None and path.read_bytes()==good
        path.write_bytes(b'corrupt cache')
        assert ns['_sound_file']('select','LOW').read_bytes()==good
        path.write_bytes(b'old corrupted again')
        make_archive(good+b'malicious')
        assert ns['_sound_file']('select','LOW') is None
        assert path.read_bytes()==b'old corrupted again'
        make_archive(good)
        path=ns['_sound_file']('select','LOW')
        assert path and path.read_bytes()==good
        st.audio_mode='LOW';st.audio_hover=False;st.audio_last=0
        assert ns['play_ui_sound']('select',force=True)
        assert played[-1][0]==str(path)
        assert not ns['play_ui_sound']('hover')
        # Volume and hover setting persist and sanitize on load.
        assert ns['set_audio_mode']('OFF')
        assert not ns['play_ui_sound']('select',force=True)
        assert ns['set_audio_mode']('LOW')
        assert ns['toggle_audio_hover']() is None
        prefs=settings/'CROWNs_Freedom_UI.json'
        data=prefs.read_text('utf-8')
        assert '"audio_mode": "LOW"' in data
        assert '"audio_hover": true' in data
        st.audio_mode='OFF';st.audio_hover=False
        ns['load_preferences']()
        assert st.audio_mode=='LOW' and st.audio_hover
    # Native menu can render the audio options at four resolutions.
    ns['SETTINGS_DIR']=None
    ns['__loader__']=None
    st.audio_mode='OFF'
    for w,h in ((2560,1440),(1920,1080),(1280,720),(854,480)):
        ns['viewport']=lambda w=w,h=h:(w,h)
        ns['open_menu']()
        assert st.opened and st.draw_ok
        ns['show_page']('STYLE')
        assert st.draw_ok
        assert any(i['name']=='AUDIO' for i in st.buttons)
        ns['toggle_style_audio']()
        assert st.style_audio_open and st.draw_ok
        buttons=[i['name'] for i in st.buttons]
        assert 'SOUND: LOW' in buttons and 'SOUND: OFF' in buttons and 'TEST SOUND' in buttons
        assert '<< BACK TO STYLE' in buttons
        ns['toggle_style_audio']()
        assert not st.style_audio_open and len(st.sliders)==3
        ns['show_page']('PLAYER')
        assert not st.style_audio_open
        ns['close_menu']()
    # Explicit player FOV readback accepts good writes; catches silently rejected writes.
    class FOV:
        def __init__(self):self.BaseFOV=90;self.VehicleFOV=95
    good=FOV()
    ns['get_pc']=lambda **k:SimpleNamespace(player=good)
    st.fov_saved=None;st.fov_original=None
    ns['change_fov'](110)
    assert good.BaseFOV==110 and good.VehicleFOV==110
    assert 'readback OK' in st.message
    class Reject:
        def __init__(self):self.__dict__['BaseFOV']=90;self.VehicleFOV=90
        def __setattr__(self,key,value):
            if key=='BaseFOV':return
            self.__dict__[key]=value
    bad=Reject()
    ns['get_pc']=lambda **k:SimpleNamespace(player=bad)
    st.fov_saved=None;st.fov_original=None
    ns['change_fov'](125)
    assert bad.BaseFOV==90 and bad.VehicleFOV==90
    assert 'FOV REJECTED' in st.message and 'restored' in st.message
    print('PASS v2.2: 18 CC0 WAV hash checks, cache repair/tamper rejection, optional playback, persisted audio settings, 4-screen UI and FOV readback')
finally:
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
