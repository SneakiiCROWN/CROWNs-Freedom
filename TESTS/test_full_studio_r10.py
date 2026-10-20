"""Original stand-ins only: no supplied third-party code or native BL4 execution."""
from pathlib import Path
from types import SimpleNamespace as N
import runpy,sys,unittest,time,json,tempfile
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
R2=runpy.run_path(str(R/'TESTS/test_echo_sandbox_r2.py'))
class FullStudioR10(unittest.TestCase):
    def setUp(self):
        R2['SandboxR2'].setUp(self)
        self.native_redraw=self.g['redraw'];self.g['redraw']=lambda:None
        self.s.controller_open_block_until=0.
        self.ps=N(_get_address=lambda:902,ExperienceState=[N(ExperienceLevel=20,ExperiencePoints=100),N(ExperienceLevel=5,ExperiencePoints=200)])
        self.pc=N(_get_address=lambda:901,PlayerState=self.ps,HasAuthority=lambda:True)
        self.g['get_pc']=lambda **kw:self.pc
        graphs=[N(ProgressGraphDef=N(PointPool=N(_name=token),GraphType=0),nodes=[N(ProgressPointsSpent=spent)]) for token,spent in (('CharacterProgressPoints',2),('SpecializationTokenPool',1))]
        self.manager=N(_get_address=lambda:903,ProgressPointsContainer=N(PointsAcquiredPerPool=[20,10]),ProgressGraphs=graphs,ProgressGraphsArrayDirty=0)
        self.actor.GbxProgressionManager=self.manager
        self.calls=[]
        def action(name,params):
            self.calls.append((name,params));track=0 if params['track']=='character' else 1
            self.ps.ExperienceState[track].ExperienceLevel=params['level'];return {'ok':False}
        self.module=N(mod=N(is_enabled=True),_runtime_pawn=lambda:self.actor,GAME=N(player_state=self.ps),_runtime_action=action)
        self.g['_reviewed_module']=lambda names,sha:self.module if names==('bl4_live',) else N()
    def call(self,name,*args):return self.g[name](*args)
    bounds=R2['SandboxR2'].bounds
    def test_track_snapshot_rejects_player_state_replacement_during_field_read(self):
        original=self.ps.ExperienceState[0]
        test=self
        class ChangingRow:
            @property
            def ExperienceLevel(obj):
                test.pc.PlayerState=N(_get_address=lambda:990,ExperienceState=[original,original])
                return original.ExperienceLevel
            @property
            def ExperiencePoints(obj):return original.ExperiencePoints
        self.ps.ExperienceState[0]=ChangingRow()
        self.assertIsNone(self.call('studio_track_read'))
    def test_missing_context_cannot_produce_progression_or_reward_snapshots(self):
        self.g['studio_context']=lambda:None
        self.assertIsNone(self.call('studio_track_read'));self.assertIsNone(self.call('studio_points_read'))
        self.assertFalse(self.call('reward_sample','BEGIN'));self.assertIsNone(self.s.r10_reward_start)
    def test_level_requires_two_presses_then_checks_live_value(self):
        self.call('studio_stage','LEVEL',23)
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
        self.assertTrue(self.call('studio_apply','LEVEL'));self.assertEqual(self.ps.ExperienceState[0].ExperienceLevel,23)
        self.assertEqual(len(self.calls),1);self.assertIn('VALUE READBACK MATCHED',self.s.r10_status)
    def test_backend_ok_without_actual_effect_stays_unconfirmed(self):
        self.module._runtime_action=lambda *a:self.calls.append(a) or {'ok':True,'level':30}
        self.call('studio_stage','LEVEL',30);self.call('studio_apply','LEVEL')
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertIsNotNone(self.s.r10_progress_job)
        self.call('studio_apply','LEVEL');self.assertEqual(len(self.calls),1)
    def test_delayed_effect_can_be_read_without_another_write(self):
        self.module._runtime_action=lambda *a:self.calls.append(a) or {'ok':True}
        self.call('studio_stage','LEVEL',22);self.call('studio_apply','LEVEL');self.call('studio_apply','LEVEL')
        self.ps.ExperienceState[0].ExperienceLevel=22
        self.assertTrue(self.call('studio_progress_readback'));self.assertEqual(len(self.calls),1)
    def test_level_change_between_presses_rearms(self):
        self.call('studio_stage','LEVEL',24);self.call('studio_apply','LEVEL');self.ps.ExperienceState[0].ExperiencePoints+=10
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
    def test_player_state_replacement_never_consumes_old_confirmation(self):
        self.call('studio_stage','LEVEL',24);self.call('studio_apply','LEVEL')
        self.pc.PlayerState=N(_get_address=lambda:999,ExperienceState=self.ps.ExperienceState)
        self.module.GAME.player_state=self.pc.PlayerState
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
    def test_level_decrease_and_reviewed_caps_are_rejected(self):
        for value in (0,61,True,float('nan')):self.assertFalse(self.call('studio_stage','LEVEL',value))
        self.call('studio_stage','LEVEL',19);self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
    def test_specialisation_has_separate_track_and_cap(self):
        self.call('studio_select_track');self.call('studio_stage','LEVEL',7)
        self.call('studio_apply','LEVEL');self.assertTrue(self.call('studio_apply','LEVEL'))
        self.assertEqual(self.ps.ExperienceState[0].ExperienceLevel,20);self.assertEqual(self.ps.ExperienceState[1].ExperienceLevel,7)
    def test_disabled_wrong_player_or_missing_reviewed_backend_blocks(self):
        self.module.mod.is_enabled=False;self.assertIsNone(self.call('studio_live_backend'))
        self.module.mod.is_enabled=True;self.module.GAME.player_state=N(_get_address=lambda:999)
        self.assertIsNone(self.call('studio_live_backend'))
        self.g['_reviewed_module']=lambda *args:None;self.assertIsNone(self.call('studio_live_backend'))
    def test_independent_xp_writer_blocks_level_changes(self):
        old=sys.modules.get('xp_gain_multiplier');sys.modules['xp_gain_multiplier']=N(mod=N(is_enabled=True))
        try:
            self.call('studio_stage','LEVEL',24);self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
        finally:
            if old is None:sys.modules.pop('xp_gain_multiplier',None)
            else:sys.modules['xp_gain_multiplier']=old
    def test_guest_and_missing_authority_do_not_write(self):
        self.call('studio_stage','LEVEL',24);self.g['session_role']=lambda:'GUEST'
        self.assertFalse(self.call('studio_apply','LEVEL'));self.g['session_role']=lambda:'SOLO';self.actor.HasAuthority=lambda:False
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
    def test_points_are_total_allowance_not_unspent_and_do_not_reset_skills(self):
        self.call('studio_stage','POINTS',25);self.call('studio_apply','POINTS')
        self.assertTrue(self.call('studio_apply','POINTS'));self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool,[25,10])
        self.assertEqual(self.manager.ProgressGraphsArrayDirty,3);self.assertEqual(self.manager.ProgressGraphs[0].nodes[0].ProgressPointsSpent,2)
        self.assertFalse(self.calls)
    def test_points_lowering_large_batch_and_missing_pool_are_rejected(self):
        for value in (19,46):self.call('studio_stage','POINTS',value);self.assertFalse(self.call('studio_apply','POINTS'))
        self.manager.ProgressGraphs[0].ProgressGraphDef.PointPool._name='UnexpectedPool'
        self.assertIsNone(self.call('studio_points_read'));self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool,[20,10])
    def test_points_spend_between_confirmation_presses_rearms(self):
        self.call('studio_stage','POINTS',24);self.call('studio_apply','POINTS');self.manager.ProgressGraphs[0].nodes[0].ProgressPointsSpent=3
        self.assertFalse(self.call('studio_apply','POINTS'));self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool[0],20)
    def test_point_partial_native_failure_is_not_retried(self):
        class Partial(list):
            def __setitem__(obj,key,val):super(Partial,obj).__setitem__(key,val);raise RuntimeError('after write')
        self.manager.ProgressPointsContainer.PointsAcquiredPerPool=Partial([20,10])
        self.call('studio_stage','POINTS',22);self.call('studio_apply','POINTS');self.assertFalse(self.call('studio_apply','POINTS'))
        self.assertIsNotNone(self.s.r10_progress_job);self.assertFalse(self.call('studio_apply','POINTS'))
        self.assertFalse(self.call('studio_progress_readback'));self.assertIsNotNone(self.s.r10_progress_job)
        self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool[0],22)
    def test_point_notification_failure_cannot_be_cleared_by_matching_allowance(self):
        class FailingNotification:
            def __init__(obj,base):obj.__dict__.update(vars(base));obj.__dict__.pop('ProgressGraphsArrayDirty')
            @property
            def ProgressGraphsArrayDirty(obj):return 0
            @ProgressGraphsArrayDirty.setter
            def ProgressGraphsArrayDirty(obj,value):raise RuntimeError('notification rejected')
        self.manager=FailingNotification(self.manager);self.actor.GbxProgressionManager=self.manager
        self.call('studio_stage','POINTS',22);self.call('studio_apply','POINTS')
        self.assertFalse(self.call('studio_apply','POINTS'))
        self.assertFalse(self.call('studio_progress_readback'));self.assertIsNotNone(self.s.r10_progress_job)
        self.assertEqual(self.manager.ProgressPointsContainer.PointsAcquiredPerPool[0],22)
        self.assertIn('notification unconfirmed',self.s.r10_status)
        self.assertFalse(self.call('studio_apply','POINTS'))
    def test_point_readback_rejects_replacement_manager_with_same_value(self):
        original=self.g['studio_progress_readback'];self.g['studio_progress_readback']=lambda:False
        self.call('studio_stage','POINTS',22);self.call('studio_apply','POINTS');self.call('studio_apply','POINTS')
        self.assertTrue(self.s.r10_progress_job['notification_returned'])
        replacement=N(**vars(self.manager));replacement._get_address=lambda:990
        self.actor.GbxProgressionManager=replacement;self.g['studio_progress_readback']=original
        self.assertFalse(self.call('studio_progress_readback'));self.assertIsNotNone(self.s.r10_progress_job)
    def test_point_notification_consumed_by_engine_does_not_require_sticky_dirty_flag(self):
        original=self.g['studio_progress_readback'];self.g['studio_progress_readback']=lambda:False
        self.call('studio_stage','POINTS',22);self.call('studio_apply','POINTS');self.call('studio_apply','POINTS')
        self.manager.ProgressGraphsArrayDirty=0;self.g['studio_progress_readback']=original
        self.assertTrue(self.call('studio_progress_readback'));self.assertIsNone(self.s.r10_progress_job)
    def test_reward_samples_reject_level_context_and_counter_changes(self):
        self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperienceLevel+=1
        self.assertFalse(self.call('reward_sample','FINISH'));self.assertFalse(self.s.r10_rewards)
        self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperiencePoints-=1
        self.assertFalse(self.call('reward_sample','FINISH'))
    def test_reward_comparison_requires_three_each_and_reports_observation_only(self):
        for group,delta in (('BASELINE',10),('SCALED',20)):
            self.call('reward_sample',group)
            for _ in range(3):
                self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperiencePoints+=delta;self.ps.ExperienceState[1].ExperiencePoints+=delta
                self.assertTrue(self.call('reward_sample','FINISH'))
        summary=self.call('reward_summary');self.assertIn('2.00x observed',summary);self.assertIn('not proof',summary)
    def test_repeated_begin_preserves_original_counter_and_samples_stay_bounded(self):
        self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperiencePoints+=5
        self.assertFalse(self.call('reward_sample','BEGIN'));self.ps.ExperienceState[0].ExperiencePoints+=5
        self.assertTrue(self.call('reward_sample','FINISH'));self.assertEqual(self.s.r10_rewards[0]['delta'],(10,0))
        for _ in range(15):self.call('reward_sample','BEGIN');self.call('reward_sample','FINISH')
        self.assertEqual(len(self.s.r10_rewards),12)
    def test_reward_export_contains_observations_without_native_identities_or_writes(self):
        self.call('reward_sample','BEGIN');self.ps.ExperienceState[0].ExperiencePoints+=10;self.call('reward_sample','FINISH')
        before=(self.ps.ExperienceState[0].ExperiencePoints,list(self.manager.ProgressPointsContainer.PointsAcquiredPerPool))
        with tempfile.TemporaryDirectory() as td:
            self.g['SETTINGS_DIR']=Path(td);self.assertTrue(self.call('export_reward_samples'))
            path=Path(td)/'CROWNs_Freedom_XP_Observations.json';data=json.loads(path.read_text())
            self.assertEqual(data['format'],'CROWN_XP_OBSERVATIONS_1');self.assertFalse(data['game_verified'])
            self.assertEqual(set(data['samples'][0]),{'group','delta','levels','seconds','current_context'})
            self.assertEqual(data['samples'][0]['delta'],[10,0]);self.assertTrue(data['samples'][0]['current_context'])
            self.assertGreaterEqual(data['samples'][0]['seconds'],0);self.assertEqual(len(list(Path(td).iterdir())),1)
        self.assertEqual(before,(self.ps.ExperienceState[0].ExperiencePoints,list(self.manager.ProgressPointsContainer.PointsAcquiredPerPool)))
        self.assertFalse(self.calls)
    def test_reward_export_failure_keeps_previous_report_and_cleans_tempfile(self):
        self.call('reward_sample','BEGIN');self.call('reward_sample','FINISH')
        with tempfile.TemporaryDirectory() as td:
            self.g['SETTINGS_DIR']=Path(td);path=Path(td)/'CROWNs_Freedom_XP_Observations.json';path.write_text('previous report')
            with patch.object(Path,'replace',side_effect=OSError('replace blocked')):
                self.assertFalse(self.call('export_reward_samples'))
            self.assertEqual(path.read_text(),'previous report');self.assertEqual(len(list(Path(td).iterdir())),1)
            self.assertIn('EXPORT FAILED',self.s.r10_status)
    def test_reward_export_requires_samples_and_labels_old_context(self):
        with tempfile.TemporaryDirectory() as td:
            self.g['SETTINGS_DIR']=Path(td);self.assertFalse(self.call('export_reward_samples'));self.assertFalse(list(Path(td).iterdir()))
            self.call('reward_sample','BEGIN');self.call('reward_sample','FINISH');self.g['studio_context']=lambda:None
            self.assertTrue(self.call('export_reward_samples'))
            data=json.loads((Path(td)/'CROWNs_Freedom_XP_Observations.json').read_text());self.assertFalse(data['samples'][0]['current_context'])
        self.g['SETTINGS_DIR']=None;self.assertFalse(self.call('export_reward_samples'))
    def test_reward_workspace_disables_unavailable_finish_and_export_then_wires_export(self):
        self.g['redraw']=self.native_redraw;self.g['SETTINGS_DIR']=None;self.call('studio_open','REWARDS')
        buttons={b['name']:b for b in self.s.buttons}
        self.assertTrue(buttons['FINISH REWARD']['disabled']);self.assertTrue(buttons['EXPORT OBSERVATIONS']['disabled'])
        with tempfile.TemporaryDirectory() as td:
            self.g['SETTINGS_DIR']=Path(td);self.call('reward_sample','BEGIN');self.call('reward_sample','FINISH')
            button=next(b for b in self.s.buttons if b['name']=='EXPORT OBSERVATIONS')
            self.assertFalse(button['disabled']);self.assertTrue(self.call('export_reward_samples'))
    def test_bonus_requires_background_callback_and_expires_while_menu_closed(self):
        self.assertFalse(self.call('bonus_start'));self.s.controller_watcher_installed=True
        before=self.call('combat_pair','OUTGOING')[1];self.assertTrue(self.call('bonus_start'));self.s.opened=False
        self.call('bonus_tick',self.s.r10_bonus['until']+1)
        self.assertIsNone(self.s.r10_bonus);self.assertEqual(self.call('combat_pair','OUTGOING')[1],before)
    def test_bonus_does_not_overwrite_outside_changes_or_stack(self):
        self.s.controller_watcher_installed=True;self.assertTrue(self.call('bonus_start'));self.assertFalse(self.call('bonus_start'))
        pair=self.call('combat_pair','OUTGOING')[0];pair.Value=7.
        self.assertFalse(self.call('bonus_stop'));self.assertEqual(pair.Value,7.);self.assertIn('OUTGOING',self.s.combat_originals)
        self.assertFalse(self.call('combat_tune','OUTGOING',2.))
    def test_combat_conflict_record_can_restore_after_owner_value_returns(self):
        self.assertTrue(self.call('combat_tune','OUTGOING',2.));pair=self.call('combat_pair','OUTGOING')[0];pair.Value=9.
        self.assertEqual(self.call('restore_combat_tuning'),0);self.assertIn('OUTGOING',self.s.combat_originals)
        pair.Value=2.;self.assertEqual(self.call('restore_combat_tuning'),1);self.assertFalse(self.s.combat_originals)
    def test_wallet_prefers_reviewed_rpc_and_verifies_exact_counter_delta(self):
        row=N(type=N(Name='Cash'),Amount=100);self.pc.CurrencyManager=N(currencies=[row])
        self.pc.Server_AddCurrency=lambda typ,amount:setattr(row,'Amount',row.Amount+amount)
        self.call('wallet_request','cash',50);self.assertTrue(self.call('wallet_request','cash',50))
        self.assertEqual(row.Amount,150);self.assertEqual(self.s.r10_wallet_history[-1]['status'],'FIELD DELTA MATCHED')
    def test_wallet_typeerror_never_falls_back_to_another_receiver(self):
        calls=[]
        def give(*args):calls.append(args);raise TypeError('after side effect')
        self.g['_native_wallet']=lambda:(object(),give,lambda *args:object())
        self.call('wallet_request','cash',50);self.assertFalse(self.call('wallet_request','cash',50))
        self.assertFalse(self.call('wallet_request','cash',50));self.assertEqual(len(calls),1)
    def test_keyboard_focus_skips_disabled_and_never_runs_actions(self):
        calls=[];self.s.buttons=[dict(disabled=False,rect=(0,0,20,20),run=lambda:calls.append(1)),dict(disabled=True,rect=(0,20,20,20)),dict(disabled=False,rect=(0,40,20,20))]
        self.s.controller_focus=0;self.call('r10_focus_cycle',1);self.assertEqual(self.s.controller_focus,2)
        self.call('r10_focus_cycle',-1);self.assertEqual(self.s.controller_focus,0);self.assertFalse(calls)
    def test_trigger_coarse_adjustment_rejects_simultaneous_confirmation(self):
        changes=[];keys={'Gamepad_RightTrigger'};self.g['key_down']=lambda pc,n:n in keys
        ref=N(adjust=lambda direction,coarse=False:changes.append((direction,coarse)))
        self.s.buttons=[dict(slider=ref)];self.s.controller_focus=0
        self.assertTrue(self.call('r10_input_tick',self.pc,1.));self.assertEqual(changes,[(1,True)])
        self.s.r10_input_keys={};keys.add('Gamepad_FaceButton_Bottom');self.call('r10_input_tick',self.pc,2.)
        self.assertEqual(len(changes),1);self.assertTrue(self.s.controller_last_keys['Gamepad_FaceButton_Bottom'])
    def test_editors_keep_their_native_tab_and_numeric_keys(self):
        self.s.numeric_editor={'text':'2'};self.g['key_down']=lambda pc,n:n in ('Tab','PageDown')
        self.assertFalse(self.call('r10_input_tick',self.pc,1.))
    def test_tick_rejects_tab_enter_before_any_action_dispatch(self):
        calls=[];keys={'Tab','Enter'};now=time.monotonic()
        self.g['key_down']=lambda pc,n:n in keys;self.g['_menu_foreground_guard']=lambda *a:False;self.g['r3_input_watch']=lambda *a:True
        self.s.viewport_last_check=now;self.s.session_last_check=now;self.s.last_poll=0;self.s.input_pc=None
        self.s.buttons=[dict(name='DANGEROUS',disabled=False,rect=(10,10,100,30),run=lambda:calls.append(1),pressed=False)]
        self.s.controller_focus=0;self.call('_tick_impl');self.assertFalse(calls)
        self.assertTrue(self.s.editor_enter_down)
    def test_mixed_gamepad_and_keyboard_select_is_consumed_once(self):
        keys={'Enter','Gamepad_FaceButton_Bottom'};self.g['key_down']=lambda pc,n:n in keys
        self.assertTrue(self.call('r10_input_tick',self.pc,1.));self.assertTrue(self.s.controller_last_keys['Gamepad_FaceButton_Bottom'])
    def test_held_page_key_in_editor_does_not_fire_after_editor_closes(self):
        self.g['key_down']=lambda pc,n:n=='PageDown';self.s.numeric_editor={'text':'2'}
        self.call('r10_input_tick',self.pc,1.);self.s.numeric_editor=None
        calls=[];self.g['r10_page_step']=lambda n:calls.append(n)
        self.assertFalse(self.call('r10_input_tick',self.pc,2.));self.assertFalse(calls)
    def test_unsigned_xinput_triggers_cover_full_byte_range(self):
        state={'left':255,'right':200}
        def get_packet(index,pointer):
            pointer._obj.pad.left_trigger=state['left'];pointer._obj.pad.right_trigger=state['right'];return 0
        self.g['_xinput_dll']=N(XInputGetState=get_packet);self.g['_game_window_foreground']=lambda:True
        old=sys.platform
        try:
            sys.platform='win32';self.g['_xinput_last_at']=-1
            self.assertTrue(self.call('_windows_raw_key','Gamepad_LeftTrigger'));self.assertTrue(self.call('_windows_raw_key','Gamepad_RightTrigger'))
            state['left']=179;self.g['_xinput_last_at']=-1;self.assertFalse(self.call('_windows_raw_key','Gamepad_LeftTrigger'))
        finally:sys.platform=old
    def test_expired_confirmation_rearms_without_dispatch(self):
        self.call('studio_stage','LEVEL',24);self.call('studio_apply','LEVEL')
        self.s.r10_confirm=(self.s.r10_confirm[0],0.)
        self.assertFalse(self.call('studio_apply','LEVEL'));self.assertFalse(self.calls)
    def test_all_studio_views_and_header_shortcut_fit_all_supported_layouts(self):
        self.g['redraw']=self.native_redraw
        for size in ((854.,480.),(1280.,720.),(1920.,1080.),(2560.,1440.)):
            self.g['viewport']=lambda size=size:size
            for view in ('LEVELS','POINTS','REWARDS','BONUS'):
                self.call('studio_open',view);self.assertTrue(self.s.draw_ok,self.s.runtime_failures);self.bounds()
                self.assertIn('PLAYER LAB',[b['name'] for b in self.s.buttons])
                self.assertTrue(self.s.sliders or view=='REWARDS')
    def test_back_and_navigation_retire_studio_without_losing_old_tools(self):
        self.call('studio_open','POINTS');self.call('_controller_back');self.assertIsNone(self.s.r10_view)
        self.call('studio_open','LEVELS');self.call('show_page','SPAWN');self.assertIsNone(self.s.r10_view)
        self.assertTrue(callable(self.g['weapon_apply']));self.assertTrue(callable(self.g['arena_bridge_request']))

    def test_studio_risk_badges_and_captions_describe_the_actual_workspace(self):
        self.s.page='LOOT'
        self.s.r10_view='REWARDS';self.assertEqual(self.call('r10_save_tag'),('READ ONLY',False))
        self.assertIn('Read-only',self.call('r10_loot_tagline'))
        self.s.r10_view='BONUS';self.assertEqual(self.call('r10_save_tag'),('TEMP/OWNED',False))
        self.assertIn('owned temporary',self.call('r10_loot_tagline'))
        for view in ('LEVELS','POINTS'):
            self.s.r10_view=view;self.assertTrue(self.call('r10_save_tag')[1]);self.assertIn('F10 cannot undo',self.call('r10_loot_tagline'))
        self.s.r10_view=None;self.s.xp_view=False;self.assertIn('do not back up saves',self.call('r10_loot_tagline'))

if __name__=='__main__':unittest.main(argv=[__file__],verbosity=2)
