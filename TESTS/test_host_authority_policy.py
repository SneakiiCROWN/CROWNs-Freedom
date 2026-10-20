"""Independent HOST-authority policy regression.

Drives the REAL session_role() through world_and_state/get_pc and verifies the
full local-vs-shared action matrix with positive and negative cases:
  SOLO, verified HOST, CLIENT, GUEST, DEDICATED, UNKNOWN, missing authority,
  and competing-mod protection.

Local/self actions (sandbox, combat tuning, wallet, studio progression, forge)
are allowed for SOLO and verified HOST. Remote/shared actions still require host
authority + explicit friend consent. Competing-mod protection is preserved.

NOTE: self.call(name, *a) already invokes the function; do NOT add trailing ().
"""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy, sys, unittest

R = Path(__file__).resolve().parents[1]
_ctx = runpy.run_path(str(R / 'TESTS' / 'test_arsenal_events.py'))
SOURCE = (R / 'SOURCE' / '__init__.py').read_text(encoding='utf-8')


class HostAuthorityPolicy(unittest.TestCase):
    def setUp(self):
        sys.modules.update({'mods_base': _ctx['mods'], 'unrealsdk': _ctx['u'],
                            'unrealsdk.hooks': _ctx['hooks'], 'unrealsdk.unreal': _ctx['unreal']})
        self.g = {'__name__': 'crown_host_auth'}
        exec(compile(SOURCE, 'crown_host_auth', 'exec'), self.g)
        self.s = self.g['State']
        self.s.safe_mode = True
        self.s.dock_mode = 'FULL'
        self.actor = NS(HasAuthority=lambda: True, _get_address=lambda: 4242)
        self.g['pawn'] = lambda: self.actor
        self.g['_session_anchor'] = lambda: ('world', 'pawn')
        self.g['echo_feedback'] = lambda e: None
        self.g['party_entries'] = lambda: [{'key': 1, 'local': True}]

    def call(self, name, *a):
        return self.g[name](*a)

    # ---- drive the real session_role via world_and_state + get_pc -------
    def set_session(self, netmode, authority=True, netmode_raises=False):
        gs = NS(PlayerArray=[NS(_get_address=lambda: 1, GetPlayerName=lambda: 'me')])
        if netmode_raises:
            world = NS(GetNetMode=lambda: (_ for _ in ()).throw(RuntimeError('no NetMode')),
                        GameState=gs)
        else:
            world = NS(GetNetMode=lambda: netmode, GameState=gs)
        self.g['world_and_state'] = lambda: (world, gs)
        pc = NS(HasAuthority=lambda: authority, _get_address=lambda: 99,
                PlayerState=gs.PlayerArray[0])
        self.g['get_pc'] = lambda possibly_loading=False: pc
        return world, gs, pc

    def _mk_tuning(self):
        for key, spec in self.g['TUNING_FIELDS'].items():
            node = self.actor
            for seg in spec[0].split('.') if spec[0] else ():
                if not hasattr(node, seg):
                    setattr(node, seg, NS())
                node = getattr(node, seg)
            setattr(node, spec[1], NS(Value=1., BaseValue=1.))

    # ===================================================================
    # session_role derivation (real path)
    # ===================================================================
    def test_netmode_int_standalone_is_solo(self):
        self.set_session(0)
        self.assertEqual(self.call('session_role'), 'SOLO')

    def test_netmode_int_listenserver_with_authority_is_host(self):
        self.set_session(2, authority=True)
        self.assertEqual(self.call('session_role'), 'HOST')

    def test_netmode_int_listenserver_without_authority_is_unknown(self):
        self.set_session(2, authority=False)
        self.assertEqual(self.call('session_role'), 'UNKNOWN')

    def test_netmode_int_client_is_guest(self):
        self.set_session(3)
        self.assertEqual(self.call('session_role'), 'GUEST')

    def test_netmode_int_dedicated_is_dedicated(self):
        self.set_session(1)
        self.assertEqual(self.call('session_role'), 'DEDICATED')

    def test_netmode_string_listenserver_is_host(self):
        self.set_session('NM_ListenServer')
        self.assertEqual(self.call('session_role'), 'HOST')

    def test_netmode_qualified_string_is_host(self):
        self.set_session('ENetMode.NM_ListenServer')
        self.assertEqual(self.call('session_role'), 'HOST')

    def test_netmode_enum_wrapper_is_host(self):
        self.set_session(NS(name='NM_ListenServer', value=2))
        self.assertEqual(self.call('session_role'), 'HOST')

    def test_netmode_raises_falls_back_to_solo_single_player(self):
        self.set_session(None, netmode_raises=True)
        self.assertEqual(self.call('session_role'), 'SOLO')

    def test_netmode_raises_multiplayer_is_unknown_never_host(self):
        gs = NS(PlayerArray=[NS(_get_address=lambda: 1), NS(_get_address=lambda: 2)])
        world = NS(GetNetMode=lambda: (_ for _ in ()).throw(RuntimeError('x')), GameState=gs)
        self.g['world_and_state'] = lambda: (world, gs)
        pc = NS(HasAuthority=lambda: True, _get_address=lambda: 99, PlayerState=gs.PlayerArray[0])
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertEqual(self.call('session_role'), 'UNKNOWN')

    # ===================================================================
    # authority helpers
    # ===================================================================
    def test_pc_has_authority_true(self):
        self.assertTrue(self.call('_pc_has_authority', self.actor))

    def test_pc_has_authority_false(self):
        self.actor.HasAuthority = lambda: False
        self.assertFalse(self.call('_pc_has_authority', self.actor))

    def test_pc_has_authority_raises_is_false(self):
        self.actor.HasAuthority = lambda: (_ for _ in ()).throw(RuntimeError('no method'))
        self.assertFalse(self.call('_pc_has_authority', self.actor))

    def test_netmode_name_normalisation(self):
        self.assertEqual(self.call('_netmode_name', 0), 'NM_Standalone')
        self.assertEqual(self.call('_netmode_name', 1), 'NM_DedicatedServer')
        self.assertEqual(self.call('_netmode_name', 2), 'NM_ListenServer')
        self.assertEqual(self.call('_netmode_name', 3), 'NM_Client')
        self.assertEqual(self.call('_netmode_name', 'NM_ListenServer'), 'NM_ListenServer')
        self.assertEqual(self.call('_netmode_name', 'ENetMode.NM_ListenServer'), 'NM_ListenServer')
        self.assertIsNone(self.call('_netmode_name', None))
        self.assertIsNone(self.call('_netmode_name', 'GARBAGE'))

    # ===================================================================
    # is_local_host_action gate
    # ===================================================================
    def test_local_action_solo_true(self):
        self.assertTrue(self.call('is_local_host_action'))

    def test_local_action_host_true(self):
        self.set_session(2)
        self.assertTrue(self.call('is_local_host_action'))

    def test_local_action_guest_false(self):
        self.set_session(3)
        self.assertFalse(self.call('is_local_host_action'))

    def test_local_action_unknown_false(self):
        self.set_session(2, authority=False)
        self.assertFalse(self.call('is_local_host_action'))

    def test_local_action_dedicated_false(self):
        self.set_session(1)
        self.assertFalse(self.call('is_local_host_action'))

    # ===================================================================
    # LOCAL/SELF gates: sandbox_solo_ready / studio_can_write
    # ===================================================================
    def test_sandbox_ready_solo(self):
        self.assertTrue(self.call('sandbox_solo_ready'))

    def test_sandbox_ready_host(self):
        self.set_session(2)
        self.assertTrue(self.call('sandbox_solo_ready'))

    def test_sandbox_ready_guest(self):
        self.set_session(3)
        self.assertFalse(self.call('sandbox_solo_ready'))

    def test_sandbox_ready_unknown(self):
        self.set_session(2, authority=False)
        self.assertFalse(self.call('sandbox_solo_ready'))

    def test_sandbox_ready_missing_authority(self):
        self.actor.HasAuthority = lambda: False
        self.assertFalse(self.call('sandbox_solo_ready'))

    def test_studio_can_write_solo(self):
        self.g['studio_context'] = lambda: NS()
        self.assertTrue(self.call('studio_can_write'))

    def test_studio_can_write_host(self):
        self.set_session(2)
        self.g['studio_context'] = lambda: NS()
        self.assertTrue(self.call('studio_can_write'))

    def test_studio_can_write_guest(self):
        self.set_session(3)
        self.g['studio_context'] = lambda: NS()
        self.assertFalse(self.call('studio_can_write'))

    # ===================================================================
    # LOCAL action: combat_tune (positive SOLO/HOST, negative otherwise)
    # ===================================================================
    def test_combat_tune_solo_allowed(self):
        self._mk_tuning()
        key = next(iter(self.g['TUNING_FIELDS']))
        self.assertTrue(self.call('combat_tune', key, 5.))

    def test_combat_tune_host_allowed(self):
        self._mk_tuning()
        self.set_session(2)
        key = next(iter(self.g['TUNING_FIELDS']))
        self.assertTrue(self.call('combat_tune', key, 5.))

    def test_combat_tune_guest_blocked(self):
        self._mk_tuning()
        self.set_session(3)
        key = next(iter(self.g['TUNING_FIELDS']))
        self.assertFalse(self.call('combat_tune', key, 5.))

    def test_combat_tune_unknown_blocked(self):
        self._mk_tuning()
        self.set_session(2, authority=False)
        key = next(iter(self.g['TUNING_FIELDS']))
        self.assertFalse(self.call('combat_tune', key, 5.))

    # ===================================================================
    # Competing-mod protection preserved (SOLO and HOST both blocked)
    # ===================================================================
    def test_competing_mod_blocks_solo(self):
        self._mk_tuning()
        key = next(iter(self.g['TUNING_FIELDS']))
        sys.modules['bl4_resources_and_cooldowns'] = NS()
        try:
            self.assertFalse(self.call('combat_tune', key, 5.))
        finally:
            sys.modules.pop('bl4_resources_and_cooldowns', None)

    def test_competing_mod_blocks_host(self):
        self._mk_tuning()
        self.set_session(2)
        key = next(iter(self.g['TUNING_FIELDS']))
        sys.modules['bl4_resources_and_cooldowns'] = NS()
        try:
            self.assertFalse(self.call('combat_tune', key, 5.))
        finally:
            sys.modules.pop('bl4_resources_and_cooldowns', None)

    # ===================================================================
    # REMOTE/SHARED actions: can_run_shared / party_permission_ok preserved
    # ===================================================================
    def test_can_run_shared_solo_true(self):
        self.assertTrue(self.call('can_run_shared', 'WORLD_TIME'))

    def test_can_run_shared_host_without_consent_false(self):
        self.set_session(2)
        self.s.party_approved = False
        self.g['party_entries'] = lambda: [{'key': 1, 'local': True}, {'key': 2, 'local': False}]
        self.assertFalse(self.call('can_run_shared', 'WORLD_TIME'))

    def test_can_run_shared_host_with_consent_true(self):
        self.set_session(2)
        self.s.party_approved = True
        self.s.party_approved_roster = (1, 2)
        self.g['party_entries'] = lambda: [{'key': 1, 'local': True}, {'key': 2, 'local': False}]
        self.assertTrue(self.call('can_run_shared', 'WORLD_TIME'))

    def test_can_run_shared_guest_false(self):
        self.set_session(3)
        self.assertFalse(self.call('can_run_shared', 'WORLD_TIME'))

    def test_can_run_shared_unknown_false(self):
        self.set_session(2, authority=False)
        self.assertFalse(self.call('can_run_shared', 'WORLD_TIME'))

    def test_party_permission_ok_host_true(self):
        self.set_session(2)
        self.s.party_approved = True
        self.s.party_approved_roster = (1,)
        self.g['party_entries'] = lambda: [{'key': 1, 'local': True}]
        self.assertTrue(self.call('party_permission_ok'))

    def test_party_permission_ok_non_host_false(self):
        self.s.party_approved = True
        self.assertFalse(self.call('party_permission_ok'))

    def test_party_permission_ok_roster_mismatch_resets(self):
        self.set_session(2)
        self.s.party_approved = True
        self.s.party_approved_roster = (1,)
        self.g['party_entries'] = lambda: [{'key': 1, 'local': True}, {'key': 9, 'local': False}]
        self.assertFalse(self.call('party_permission_ok'))
        self.assertFalse(self.s.party_approved)

    # ===================================================================
    # Wallet: local self-write allowed SOLO/HOST, blocked otherwise
    # ===================================================================
    def test_wallet_receiver_solo(self):
        self.assertIsNotNone(self.call('_wallet_receiver'))

    def test_wallet_receiver_host(self):
        self.set_session(2)
        self.assertIsNotNone(self.call('_wallet_receiver'))

    def test_wallet_receiver_guest_blocked(self):
        self.set_session(3)
        self.assertIsNone(self.call('_wallet_receiver'))

    def test_wallet_receiver_unknown_blocked(self):
        self.set_session(2, authority=False)
        self.assertIsNone(self.call('_wallet_receiver'))

    # ===================================================================
    # Forge/spawn: local request allowed SOLO/HOST, blocked otherwise
    # ===================================================================
    def _arm_spawn(self):
        self.s.spawn_level = 50
        self.s.spawn_count = 1
        self.s.forge_uncertain_anchor = None
        self.s.spawn_view = 'BROWSE'

    def test_spawn_request_solo_arms(self):
        self._arm_spawn()
        self.call('spawn_request')
        self.assertEqual(self.s.forge_stage, 'ARMED_AWAITING_CONFIRM')

    def test_spawn_request_host_arms(self):
        self._arm_spawn()
        self.set_session(2)
        self.call('spawn_request')
        self.assertEqual(self.s.forge_stage, 'ARMED_AWAITING_CONFIRM')

    def test_spawn_request_guest_blocked(self):
        self._arm_spawn()
        self.set_session(3)
        self.call('spawn_request')
        self.assertEqual(self.s.forge_stage, 'BLOCKED_NOT_LOCAL_HOST')

    def test_spawn_request_unknown_blocked(self):
        self._arm_spawn()
        self.set_session(2, authority=False)
        self.call('spawn_request')
        self.assertEqual(self.s.forge_stage, 'BLOCKED_NOT_LOCAL_HOST')


if __name__ == '__main__':
    unittest.main(exit=False, verbosity=0)
