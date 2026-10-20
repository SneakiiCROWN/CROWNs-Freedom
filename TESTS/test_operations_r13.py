"""End-to-end original stand-ins; never execute supplied community source."""
from pathlib import Path
from types import SimpleNamespace as N
import runpy,unittest,time
R=Path(__file__).resolve().parents[1]
P=runpy.run_path(str(R/'TESTS/test_field_engineering_r12.py'))
A=runpy.run_path(str(R/'TESTS/test_reconciled_r8.py'))
class Operations(unittest.TestCase):
    def setUp(self):
        P['FieldEngineering'].setUp(self)
        self.s.r10_bonus=None;self.s.controller_watcher_installed=True
    def call(self,name,*args,**kwargs):return self.g[name](*args,**kwargs)
    bounds=runpy.run_path(str(R/'TESTS/test_echo_sandbox_r2.py'))['SandboxR2'].bounds
    def native_xp(self):
        module=P['FieldEngineering'].xp(self);self.writes=[]
        def setter(value):
            self.writes.append(value);module.actual=2.*value;module._RUNTIME_STATE['experience_reward_scale']=value
            return {'ok':True}
        module._runtime_set_combat_xp_scale=setter;return module
    def addon(self):
        self.addon_module=N(mod=N(is_enabled=True),xp_multiplier=N(value=1.5),_player_state=lambda:self.ps,_armed=True,_topups=3)
        self.g['_reviewed_module']=lambda names,sha:self.addon_module if names==('xp_gain_multiplier',) else None
        self.s.xp_external_view=True;self.commands=[]
        def command(text):self.commands.append(text);self.addon_module.xp_multiplier.value=float(text.split()[1])
        self.pc.ConsoleCommand=command;return self.addon_module
    def arena(self):return A['ReconciledR8'].arena(self)
    def test_native_xp_preset_apply_observe_and_owned_restore(self):
        module=self.native_xp();self.s.xp_external_view=False
        self.assertTrue(self.call('r13_xp_preset',3.));self.assertFalse(self.writes);self.assertEqual(self.s.xp_draft,3.)
        self.assertTrue(self.call('r13_xp_apply'));self.assertEqual(module.actual,6.)
        self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperiencePoints+=15
        self.assertTrue(self.call('reward_sample','FINISH'));self.assertEqual(self.s.r10_rewards[-1]['delta'],(15,0))
        self.assertTrue(self.call('r13_xp_restore'));self.assertEqual(module.actual,2.);self.assertEqual(self.writes,[3.,1.])
    def test_all_native_presets_stage_without_any_award_or_modifier_write(self):
        self.native_xp();self.s.xp_external_view=False
        for value in (1.,2.,3.,5.,10.):self.assertTrue(self.call('r13_xp_preset',value));self.assertEqual(self.s.xp_draft,value)
        self.assertFalse(self.writes);self.assertFalse(self.call('r13_xp_preset',True))
    def test_addon_read_stage_confirm_and_config_readback_without_inferred_awards(self):
        module=self.addon();xp=self.ps.ExperienceState[0].ExperiencePoints
        self.assertTrue(self.call('r13_xp_preset',5.));self.assertFalse(self.commands)
        self.assertFalse(self.call('r13_xp_apply'));self.assertTrue(self.call('r13_xp_apply'))
        self.assertEqual(self.commands,['xp_mult 5.00']);self.assertEqual(module.xp_multiplier.value,5.)
        self.assertEqual(self.ps.ExperienceState[0].ExperiencePoints,xp);self.assertIn('CONFIG READBACK',self.s.xp_status)
    def test_addon_partial_exception_cannot_be_cleared_by_matching_config(self):
        module=self.addon();self.s.external_xp_draft=3.
        def command(text):self.commands.append(text);module.xp_multiplier.value=3.;raise RuntimeError('partial reset')
        self.pc.ConsoleCommand=command;self.call('r13_xp_apply');self.assertFalse(self.call('r13_xp_apply'))
        self.assertFalse(self.call('r13_xp_read'));self.assertFalse(self.call('r13_xp_apply'))
        self.assertEqual(len(self.commands),1);self.assertIsNotNone(self.s.r13_xp_job)
        self.assertFalse(self.call('xp_external_request'));self.assertEqual(len(self.commands),1)
    def test_addon_delayed_config_readback_recovers_without_repeating_command(self):
        module=self.addon();self.s.external_xp_draft=2.;self.pc.ConsoleCommand=lambda text:self.commands.append(text)
        self.call('r13_xp_apply');self.assertFalse(self.call('r13_xp_apply'));module.xp_multiplier.value=2.
        self.assertTrue(self.call('r13_xp_read'));self.assertIsNone(self.s.r13_xp_job);self.assertEqual(len(self.commands),1)
    def test_addon_numeric_entry_roundtrips_without_silent_command_rounding(self):
        module=self.addon();self.s.external_xp_draft=.123456789
        self.assertFalse(self.call('r13_xp_apply'));self.assertTrue(self.call('r13_xp_apply'))
        self.assertEqual(module.xp_multiplier.value,.123456789);self.assertIsNone(self.s.r13_xp_job)
    def test_addon_confirmation_binds_player_state_and_config_baseline(self):
        module=self.addon();self.s.external_xp_draft=2.;self.call('r13_xp_apply');module.xp_multiplier.value=1.6
        self.assertFalse(self.call('r13_xp_apply'));self.assertFalse(self.commands)
        self.pc.PlayerState=N(_get_address=lambda:990)
        self.assertFalse(self.call('r13_xp_apply'));self.assertFalse(self.commands)
    def test_addon_disabled_or_wrong_player_is_blocked(self):
        module=self.addon();module.mod.is_enabled=False;self.assertFalse(self.call('r13_xp_read'))
        module.mod.is_enabled=True;module._player_state=lambda:N(_get_address=lambda:999)
        self.assertFalse(self.call('r13_xp_apply'));self.assertFalse(self.commands)
    def test_addon_vanilla_is_staged_never_silently_writes(self):
        self.addon();self.assertFalse(self.call('r13_xp_restore'));self.assertEqual(self.s.external_xp_draft,1.);self.assertFalse(self.commands)
    def test_switching_sources_cannot_abandon_an_owner_or_ambiguous_attempt(self):
        self.s.xp_owner={};self.assertFalse(self.call('r13_xp_source','REWARD'))
        self.s.xp_owner=None;self.s.r12_xp_attempt={};self.assertFalse(self.call('r13_xp_source','NATIVE'))
    def test_every_bonus_profile_writes_its_fields_and_restores_exact_baseline(self):
        for profile in self.g['R13_BONUSES']:
            before={key:self.call('combat_pair',key)[1] for key,direction in self.g['R13_BONUSES'][profile][1]}
            self.assertTrue(self.call('r13_bonus_choose',profile));self.assertTrue(self.call('bonus_start'))
            for key,direction in self.g['R13_BONUSES'][profile][1]:
                current=self.call('combat_pair',key)[1][0]
                self.assertGreater(current,before[key][0]) if direction=='UP' else self.assertLess(current,before[key][0])
            self.assertTrue(self.call('bonus_stop'))
            for key,value in before.items():self.assertEqual(self.call('combat_pair',key)[1],value)
    def test_multifield_bonus_preflight_never_partially_applies_missing_field(self):
        self.call('r13_bonus_choose','ELEMENTAL');original=self.g['combat_pair']
        self.g['combat_pair']=lambda key,*args:None if key=='CORROSIVE' else original(key,*args)
        self.assertFalse(self.call('bonus_start'));self.assertFalse(self.s.combat_originals)
        self.assertEqual(original('FIRE')[1],(1.,1.))
    def test_multifield_failure_rolls_back_prior_owned_fields(self):
        self.call('r13_bonus_choose','ELEMENTAL');original=self.g['combat_tune']
        self.g['combat_tune']=lambda key,value:False if key=='CORROSIVE' else original(key,value)
        self.assertFalse(self.call('bonus_start'));self.assertFalse(self.s.combat_originals);self.assertIsNone(self.s.r10_bonus)
        self.assertEqual(self.call('combat_pair','FIRE')[1],(1.,1.))
    def test_multifield_expiry_preserves_outside_change_and_retains_only_conflict(self):
        self.call('r13_bonus_choose','ELEMENTAL');self.assertTrue(self.call('bonus_start'))
        self.call('combat_pair','FIRE')[0].Value=7.;self.s.opened=False
        self.call('bonus_tick',self.s.r10_bonus['until']+1)
        self.assertEqual(self.call('combat_pair','FIRE')[1][0],7.);self.assertEqual(set(self.s.combat_originals),{'FIRE'})
        self.assertEqual(self.call('combat_pair','SHOCK')[1],(1.,1.));self.assertIsNone(self.s.r10_bonus)
    def test_bonus_rejects_stacking_profile_switch_and_no_callback(self):
        self.call('bonus_start');self.assertFalse(self.call('r13_bonus_choose','GUARD'));self.assertFalse(self.call('bonus_start'))
        self.call('bonus_stop');self.s.controller_watcher_installed=False;self.assertFalse(self.call('bonus_start'))
    def test_arena_auto_observation_reports_birth_and_end_and_never_destroys(self):
        self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request')
        self.s.opened=True;self.s.page='ARENA';self.s.encounter_route='ARENA';self.count=1
        self.call('r13_arena_tick',10.);self.assertEqual(self.s.r13_arena_snapshot['alive'],1)
        self.count=0;self.dead=True;self.call('r13_arena_tick',11.1)
        self.assertIsNone(self.s.arena_bridge_issued);self.assertFalse(self.destroyed)
    def test_arena_automatic_readback_is_throttled_and_pauses_on_exception(self):
        self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request')
        self.s.opened=True;self.s.page='ARENA';self.s.encounter_route='ARENA';reads=[]
        self.slot.pointer=lambda:reads.append(1) or (_ for _ in ()).throw(RuntimeError('weak ref unavailable'))
        self.call('r13_arena_tick',10.);self.call('r13_arena_tick',10.1);self.call('r13_arena_tick',12.)
        self.assertEqual(len(reads),1);self.assertTrue(self.s.r13_arena_fault)
    def test_arena_slot_reuse_never_dereferences_recycled_slot(self):
        self.arena();self.call('arena_bridge_request');self.call('arena_bridge_request');self.slot.handed_ns=99
        self.slot.pointer=lambda:self.fail('recycled native pointer read')
        self.assertFalse(self.call('arena_bridge_read',quiet=True));self.assertEqual(self.s.r13_arena_snapshot['unconfirmed'],1)
    def test_arena_search_resets_both_catalogue_indices(self):
        self.s.encounter_input=N(GetText=lambda:'test');self.s.arena_bridge_page=44;self.s.arena_bridge_selected=133
        self.assertTrue(self.call('encounter_search'));self.assertEqual(self.s.arena_bridge_page,0);self.assertEqual(self.s.arena_bridge_selected,0)
    def test_operations_surfaces_fit_all_supported_resolutions(self):
        self.arena();self.g['redraw']=self.native_redraw
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            for view in ('XP','BONUS','ARENA'):
                if view=='ARENA':self.s.encounter_view='CONTROLS';self.call('show_page','ARENA')
                elif view=='BONUS':self.call('studio_open','BONUS')
                else:self.s.xp_external_view=False;self.call('r3_open_tool','LOOT','XP')
                self.assertTrue(self.s.draw_ok,self.s.runtime_failures);self.bounds()

    def test_forge_workbench_controls_fit_and_numeric_edits_cancel_confirmation(self):
        self.g['redraw']=self.native_redraw
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            self.s.forge_compare_view=False;self.s.spawn_view='TOOLS';self.call('show_page','SPAWN')
            self.assertTrue(self.s.draw_ok,self.s.runtime_failures);self.bounds()
            names=[b['name'] for b in self.s.buttons]
            self.assertIn('FIND ITEM',names);self.assertIn('REQUEST ITEM',names);self.assertIn('COMPARE',names)
            next(b for b in self.s.buttons if b['name']=='COMPARE')['run']()
            self.assertTrue(self.s.forge_compare_view);self.assertTrue(self.s.draw_ok);self.bounds()
            self.assertIn('CHECK FORGE API',[b['name'] for b in self.s.buttons])
        self.s.spawn_pending=('armed',);self.s.spawn_expires=time.monotonic()+7
        self.assertTrue(self.call('_forge_numeric_stage','level',42));self.assertIsNone(self.s.spawn_pending)
        self.assertEqual(self.s.spawn_level,42);self.assertFalse(self.call('_forge_numeric_stage','count',4))

    def test_departed_addon_context_can_be_retired_without_loaded_backend(self):
        self.addon();self.s.r13_xp_job=dict(context=('departed',),module=None,target=3.,returned=False)
        self.g['_reviewed_module']=lambda *args:None
        self.assertTrue(self.call('r13_xp_source','NATIVE'));self.assertIsNone(self.s.r13_xp_job)
        self.s.r13_xp_job=dict(context=('departed',));self.g['studio_context']=lambda:None
        self.assertFalse(self.call('r13_xp_source','NATIVE'));self.assertIsNotNone(self.s.r13_xp_job)

    def test_hover_cannot_interrupt_success_cue_but_explicit_audition_can(self):
        self.s.safe_mode=False;self.s.audio_mode='LOW';self.s.audio_hover=True;self.s.audio_last=0
        self.g['_sound_file']=lambda *args:'verified.wav';played=[]
        self.g['_windows_play_wav']=lambda path:played.append(path) or 'STAND-IN'
        now=[10.];self.g['time']=N(monotonic=lambda:now[0])
        self.assertTrue(self.call('play_ui_sound','confirm'));now[0]=10.2
        self.assertFalse(self.call('play_ui_sound','hover'));self.assertEqual(len(played),1)
        self.assertTrue(self.call('play_ui_sound','hover',force=True));now[0]=10.4
        self.assertTrue(self.call('play_ui_sound','hover'));self.assertEqual(len(played),3)
        self.s.safe_mode=True;self.assertFalse(self.call('play_ui_sound','confirm',force=True))

    def test_xp_recipes_preserve_addon_source_and_never_apply_while_loading(self):
        self.addon();self.s.external_xp_draft=.5
        recipe=self.call('recipe_capture','XP');self.assertEqual(recipe,{'source':'REWARD','scale':.5})
        self.assertTrue(self.call('recipe_stage','XP',recipe));self.assertTrue(self.s.xp_external_view);self.assertFalse(self.commands)
        self.assertTrue(self.call('recipe_stage','XP',{'source':'NATIVE','scale':3.}))
        self.assertFalse(self.s.xp_external_view);self.assertEqual(self.s.xp_draft,3.)
        self.s.r12_xp_attempt={};self.assertFalse(self.call('recipe_stage','XP',recipe));self.assertFalse(self.s.xp_external_view)

    def test_legacy_xp_toggle_cannot_bypass_partial_request_lock(self):
        self.s.r12_xp_attempt={};route=self.s.xp_route
        self.assertFalse(self.call('xp_route_toggle'));self.assertEqual(self.s.xp_route,route)

    def test_legacy_encounter_recipes_select_bms_without_losing_arena_job(self):
        row=self.g['ENCOUNTER_CATALOGUE'][0];recipe={'code':row[0],'quantity':1,'distance':1000.}
        self.s.encounter_route='ARENA';self.s.arena_bridge_issued={}
        self.assertFalse(self.call('recipe_stage','ENCOUNTER',recipe));self.assertEqual(self.s.encounter_route,'ARENA')
        self.assertFalse(self.call('encounter_route_toggle'));self.assertIsNotNone(self.s.arena_bridge_issued)
        self.s.arena_bridge_issued=None;self.assertTrue(self.call('recipe_stage','ENCOUNTER',recipe))
        self.assertEqual(self.s.encounter_route,'BMS');self.assertEqual(self.s.encounter_distance,1000.)

    def test_xp_dashboard_does_not_overlap_legacy_decoration(self):
        art=[];self.g['optional_art_image']=lambda parent,name,x,y,w,h,**kw:art.append((name,y,h)) or True
        self.g['redraw']=self.native_redraw;self.g['viewport']=lambda:(2560.,1440.)
        self.call('r3_open_tool','LOOT','XP')
        cards=[(y,h) for name,y,h in art if name=='FIELD_CARD_XP'];self.assertEqual(len(cards),2)
        for name,y,h in art:
            if name in ('TRADER_LEFT','TRADER_RIGHT'):self.assertGreaterEqual(y,max(cy+ch for cy,ch in cards))

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
