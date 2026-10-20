"""Regression tests for R18/R19 crash-safety wrappers.

Covers _safe_pc_call, _pc_wrapper_valid, _safe_attr_set, _safe_create_widget,
and _safe_native_call with positive and negative cases.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import runpy, sys, unittest

R = Path(__file__).resolve().parents[1]
_ctx = runpy.run_path(str(R / 'TESTS' / 'test_arsenal_events.py'))
SOURCE = (R / 'SOURCE' / '__init__.py').read_text(encoding='utf-8')


class CrashSafety(unittest.TestCase):
    def setUp(self):
        sys.modules.update({'mods_base': _ctx['mods'], 'unrealsdk': _ctx['u'],
                            'unrealsdk.hooks': _ctx['hooks'], 'unrealsdk.unreal': _ctx['unreal']})
        self.g = {'__name__': 'crown_crash_safety'}
        exec(compile(SOURCE, 'crown_crash_safety', 'exec'), self.g)
        self.s = self.g['State']
        self.actor = NS(HasAuthority=lambda: True, _get_address=lambda: 4242)
        self.g['pawn'] = lambda: self.actor
        self.g['_session_anchor'] = lambda: ('world', 'pawn')

    def call(self, name, *a):
        return self.g[name](*a)

    # ---- _pc_wrapper_valid ----
    def test_wrapper_valid_none_is_false(self):
        self.assertFalse(self.call('_pc_wrapper_valid', None))

    def test_wrapper_valid_live_pc(self):
        pc = NS(_get_address=lambda: 99, HasAuthority=lambda: True)
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertTrue(self.call('_pc_wrapper_valid', pc))

    def test_wrapper_valid_stale_pc(self):
        pc = NS(_get_address=lambda: 99, HasAuthority=lambda: True)
        other = NS(_get_address=lambda: 100, HasAuthority=lambda: True)
        self.g['get_pc'] = lambda possibly_loading=False: other
        self.assertFalse(self.call('_pc_wrapper_valid', pc))

    def test_wrapper_valid_get_pc_raises(self):
        pc = NS(_get_address=lambda: 99, HasAuthority=lambda: True)
        def boom(possibly_loading=False):
            raise RuntimeError('no pc')
        self.g['get_pc'] = boom
        self.assertFalse(self.call('_pc_wrapper_valid', pc))

    # ---- _safe_pc_call ----
    def test_safe_pc_call_none_pc(self):
        self.assertIsNone(self.call('_safe_pc_call', None, 'foo'))

    def test_safe_pc_call_stale_pc(self):
        pc = NS(_get_address=lambda: 99, foo=lambda: 'bar')
        other = NS(_get_address=lambda: 100)
        self.g['get_pc'] = lambda possibly_loading=False: other
        self.assertIsNone(self.call('_safe_pc_call', pc, 'foo'))

    def test_safe_pc_call_missing_method(self):
        pc = NS(_get_address=lambda: 99)
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertIsNone(self.call('_safe_pc_call', pc, 'nonexistent'))

    def test_safe_pc_call_success(self):
        pc = NS(_get_address=lambda: 99, foo=lambda x: x + 1)
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertEqual(self.call('_safe_pc_call', pc, 'foo', 5), 6)

    def test_safe_pc_call_method_raises(self):
        def boom(x):
            raise RuntimeError('native crash')
        pc = NS(_get_address=lambda: 99, foo=boom)
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertIsNone(self.call('_safe_pc_call', pc, 'foo', 5))

    def test_safe_pc_call_custom_default(self):
        # With default provided, None PC returns default
        self.assertEqual(self.g['_safe_pc_call'](None, 'foo', default='FALLBACK'), 'FALLBACK')

    # ---- _safe_attr_set ----
    def test_safe_attr_set_none_pc(self):
        self.assertFalse(self.call('_safe_attr_set', None, 'flag', True))

    def test_safe_attr_set_stale_pc(self):
        pc = NS(_get_address=lambda: 99)
        other = NS(_get_address=lambda: 100)
        self.g['get_pc'] = lambda possibly_loading=False: other
        self.assertFalse(self.call('_safe_attr_set', pc, 'flag', True))

    def test_safe_attr_set_success(self):
        pc = NS(_get_address=lambda: 99)
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertTrue(self.call('_safe_attr_set', pc, 'flag', True))
        self.assertTrue(pc.flag)

    def test_safe_attr_set_raises(self):
        class BadPC:
            _get_address = lambda self: 99
            def __setattr__(self, k, v):
                raise RuntimeError('no setattr')
        pc = BadPC()
        self.g['get_pc'] = lambda possibly_loading=False: pc
        self.assertFalse(self.call('_safe_attr_set', pc, 'flag', True))

    # ---- _safe_create_widget ----
    def test_safe_create_widget_none_class(self):
        self.g['cls'] = lambda path: None
        self.assertIsNone(self.call('_safe_create_widget', '/Script/UMG.UserWidget', None))

    def test_safe_create_widget_construct_fails(self):
        self.g['cls'] = lambda path: object()
        self.g['unrealsdk'].construct_object = lambda cls, outer: None
        self.assertIsNone(self.call('_safe_create_widget', '/Script/UMG.UserWidget', None))

    def test_safe_create_widget_success(self):
        widget = NS(name='widget')
        self.g['cls'] = lambda path: object()
        self.g['unrealsdk'].construct_object = lambda cls, outer: widget
        result = self.call('_safe_create_widget', '/Script/UMG.UserWidget', None)
        self.assertIs(result, widget)

    # ---- _safe_native_call ----
    def test_safe_native_call_none_obj(self):
        self.assertIsNone(self.call('_safe_native_call', None, 'foo'))

    def test_safe_native_call_missing_method(self):
        obj = NS()
        self.assertIsNone(self.call('_safe_native_call', obj, 'nonexistent'))

    def test_safe_native_call_success(self):
        obj = NS(foo=lambda x, y: x + y)
        self.assertEqual(self.call('_safe_native_call', obj, 'foo', 3, 4), 7)

    def test_safe_native_call_raises(self):
        def boom():
            raise RuntimeError('native')
        obj = NS(foo=boom)
        self.assertIsNone(self.call('_safe_native_call', obj, 'foo'))

    def test_safe_native_call_custom_default(self):
        self.assertEqual(self.g['_safe_native_call'](None, 'foo', default='FB'), 'FB')

    # ---- attempt() with native refusal ----
    def test_attempt_false_return_is_refusal(self):
        obj = NS(foo=lambda: False)
        self.assertFalse(self.call('attempt', obj, 'foo'))

    def test_attempt_true_return_accepted(self):
        obj = NS(foo=lambda: True)
        self.assertTrue(self.call('attempt', obj, 'foo'))

    def test_attempt_exception_is_false(self):
        def boom():
            raise RuntimeError('native')
        obj = NS(foo=boom)
        self.assertFalse(self.call('attempt', obj, 'foo'))

    def test_attempt_missing_method_is_false(self):
        obj = NS()
        self.assertFalse(self.call('attempt', obj, 'nonexistent'))

    # ---- key_down with stale PC ----
    def test_key_down_stale_pc_returns_false(self):
        pc = NS(_get_address=lambda: 99, IsInputKeyDown=lambda key: True)
        other = NS(_get_address=lambda: 100)
        self.g['get_pc'] = lambda possibly_loading=False: other
        self.assertFalse(self.call('key_down', pc, 'F7'))

    def test_key_down_none_pc_returns_false(self):
        self.assertFalse(self.call('key_down', None, 'F7'))

    # ---- release_input with stale PC ----
    def test_release_input_stale_pc_no_crash(self):
        pc = NS(_get_address=lambda: 99)
        other = NS(_get_address=lambda: 100)
        self.g['get_pc'] = lambda possibly_loading=False: other
        self.g['State'].input_pc = pc
        self.g['State'].input_saved = {'bShowMouseCursor': False}
        self.g['State'].input_move_ignored_original = False
        self.g['State'].input_look_ignored_original = False
        self.g['State'].input_mode_owned = True
        # Should not raise
        self.call('release_input')
        self.assertIsNone(self.g['State'].input_pc)

    def test_release_input_none_pc_no_crash(self):
        self.g['State'].input_pc = None
        # Should not raise
        self.call('release_input')


if __name__ == '__main__':
    unittest.main(exit=False, verbosity=0)