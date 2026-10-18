import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from harness.core import Adb, Harness, HarnessError, HOME, PKG, canonical_component, configure_launcher, digest, save
from harness.mcp import dispatch


class FakeTV:
    serial = 'tv-test:5555'
    def __init__(self):
        self.packages = {'com.vendor.ads': 0, 'com.vendor.metrics': 2,
                         'com.google.android.apps.tv.launcherx': 0}
        self.home = 'com.google.android.apps.tv.launcherx/.HomeActivity'
        self.fail = None
        self.writes = []
        self.fingerprint = 'test/build/34'
    def shell(self, *args):
        a = list(args)
        if a[0] == 'getprop':
            return {'ro.build.fingerprint': self.fingerprint, 'ro.serialno': 'TEST123'}.get(a[1], 'test')
        if a[:3] == ['pm', 'list', 'features']:
            return 'feature:android.software.leanback'
        if a[:3] == ['pm', 'list', 'packages']:
            return '\n'.join('package:' + p for p, state in sorted(self.packages.items())
                             if '-d' not in a or state in (2, 3, 4))
        if a[:2] == ['dumpsys', 'package']:
            return '  User 0: installed=true hidden=false enabled=' + str(self.packages[a[2]])
        if a[:3] == ['cmd', 'package', 'resolve-activity']:
            return self.home
        self.writes.append(a)
        if a[0] == 'pm':
            states = {'default-state': 0, 'enable': 1, 'disable': 2, 'disable-user': 3, 'disable-until-used': 4}
            self.packages[a[-1]] = states[a[1]]
            if self.fail == a[-1]:
                self.fail = None
                raise HarnessError('Simulated disconnect after write')
            return 'ok'
        if a[:3] == ['cmd', 'package', 'set-home-activity']:
            self.home = a[-1]
            return 'Success'
        if a[:3] == ['dumpsys', 'activity', 'activities']:
            return 'mResumedActivity: ' + self.home
        if a[0] in ('am', 'input'):
            return 'ok'
        raise AssertionError(a)
    def run(self, *args, **kwargs):
        if args[0] == 'install':
            self.packages[PKG] = 0
            return 'Success'
        if args[0] == 'uninstall':
            self.packages.pop(PKG)
            return 'Success'
        raise AssertionError(args)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tv = FakeTV()
        self.h = Harness(self.tv, self.temp.name)
    def test_silent_android_commands_have_valid_exit_marker(self):
        adb = Adb('tv-test:5555')
        for output in ('__TVH_EXIT__0', 'result\n__TVH_EXIT__0'):
            with patch.object(adb, 'run', return_value=output):
                self.assertIn(adb.shell('input', 'keyevent', 'KEYCODE_HOME'), ('', 'result'))
        with patch.object(adb, 'run', return_value='failed\n__TVH_EXIT__1'):
            with self.assertRaises(HarnessError):
                adb.shell('input', 'keyevent', 'KEYCODE_HOME')
    def test_android_components_compare_short_and_full_names(self):
        self.assertEqual(canonical_component(HOME), canonical_component('com.gathin.tvhome/com.gathin.tvhome.MainActivity'))
    def test_inventory_is_read_only(self):
        inv = self.h.inventory()
        self.assertIn('com.vendor.ads', inv['packages'])
        self.assertEqual(self.tv.writes, [])
    def test_plan_has_no_tv_side_effect(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.assertEqual(p['before']['com.vendor.ads'], 0)
        self.assertEqual(self.tv.writes, [])
    def test_apply_and_restore_exact_default_and_disabled_states(self):
        p = self.h.plan({'disable': ['com.vendor.ads'], 'enable': ['com.vendor.metrics']})
        self.assertEqual(self.h.apply(p['id'])['status'], 'completed')
        self.assertEqual(self.tv.packages['com.vendor.ads'], 3)
        self.assertEqual(self.h.restore(p['id'])['status'], 'restored')
        self.assertEqual(self.tv.packages['com.vendor.ads'], 0)
        self.assertEqual(self.tv.packages['com.vendor.metrics'], 2)
    def test_partial_failure_is_rolled_back_including_uncertain_write(self):
        p = self.h.plan({'disable': ['com.vendor.ads'], 'enable': ['com.vendor.metrics']})
        self.tv.fail = 'com.vendor.ads'
        result = self.h.apply(p['id'])
        self.assertEqual(result['status'], 'failed_rolled_back')
        self.assertEqual(self.tv.packages['com.vendor.ads'], 0)
        self.assertEqual(self.tv.packages['com.vendor.metrics'], 2)
    def test_protected_packages_and_injection_are_blocked(self):
        for pkg in ('com.google.android.apps.tv.launcherx', 'com.android.settings',
                    'com.vendor.update', 'com.vendor.ads;reboot'):
            with self.assertRaises(HarnessError):
                self.h.plan({'disable': [pkg]})
        self.assertEqual(self.tv.writes, [])
    def test_unknown_and_contradictory_actions_are_blocked(self):
        for request in ({'shell': 'reboot'}, {'disable': 'com.vendor.ads'},
                        {'disable': ['com.vendor.ads'], 'enable': ['com.vendor.ads']},
                        {'disable': ['com.vendor.absent']}, {'set_home': 'yes'}):
            with self.assertRaises(HarnessError):
                self.h.plan(request)
    def test_drift_blocks_all_writes(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.tv.packages['com.vendor.ads'] = 1
        with self.assertRaises(HarnessError):
            self.h.apply(p['id'])
        self.assertEqual(self.tv.writes, [])
    def test_modified_plan_is_rejected(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        p['steps'][0]['package'] = 'com.android.settings'
        save(self.h.path('plans', p['id']), p)
        with self.assertRaises(HarnessError):
            self.h.apply(p['id'])
    def test_expired_plan_is_rejected(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        p.pop('integrity')
        p['expires_at'] = 0
        p['integrity'] = digest(p)
        save(self.h.path('plans', p['id']), p)
        with self.assertRaises(HarnessError):
            self.h.apply(p['id'])
    def test_plan_cannot_be_replayed(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.h.apply(p['id'])
        with self.assertRaises(HarnessError):
            self.h.apply(p['id'])
    def test_wrong_device_blocks_restore(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.h.apply(p['id'])
        self.tv.fingerprint = 'another-tv'
        writes = len(self.tv.writes)
        self.assertEqual(self.h.restore(p['id'])['status'], 'recovery_required')
        self.assertEqual(len(self.tv.writes), writes)
    def test_crash_journal_can_be_restored(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.tv.packages['com.vendor.ads'] = 3
        run = {'id': p['id'], 'status': 'running', 'plan': p,
               'attempted': p['steps'], 'verified': [], 'recovery': []}
        save(self.h.path('runs', p['id']), run)
        self.assertEqual(self.h.restore(p['id'])['status'], 'restored')
        self.assertEqual(self.tv.packages['com.vendor.ads'], 0)
    def test_select_home_retains_stock_launcher_and_restores(self):
        self.tv.packages[PKG] = 0
        stock = self.tv.home
        p = self.h.plan({'set_home': True})
        self.assertEqual(self.h.apply(p['id'])['status'], 'completed')
        self.assertEqual(self.tv.home, HOME)
        self.assertEqual(self.tv.packages[stock.split('/')[0]], 0)
        self.h.restore(p['id'])
        self.assertEqual(self.tv.home, stock)
    def test_apk_install_home_and_removal_on_restore(self):
        apk = Path(self.temp.name) / 'test.apk'
        apk.write_bytes(b'test-apk')
        with patch('harness.core.shutil.which', return_value='/test/apkanalyzer'), \
             patch('harness.core.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = PKG + '\n'
            p = self.h.plan({'apk': str(apk), 'set_home': True})
        self.assertEqual(self.h.apply(p['id'])['status'], 'completed')
        self.assertEqual(self.h.restore(p['id'])['status'], 'restored')
        self.assertNotIn(PKG, self.tv.packages)
    def test_pending_recovery_blocks_new_writes(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        record = {'id': 'a' * 32, 'status': 'recovery_required'}
        save(self.h.path('runs', record['id']), record)
        with self.assertRaises(HarnessError):
            self.h.apply(p['id'])
        self.assertEqual(self.tv.writes, [])
    def test_restore_offline_retains_recovery_record(self):
        p = self.h.plan({'disable': ['com.vendor.ads']})
        self.h.apply(p['id'])
        with patch.object(self.h, 'inventory', side_effect=HarnessError('offline')):
            result = self.h.restore(p['id'])
        self.assertEqual(result['status'], 'recovery_required')
        self.assertEqual(self.h.load('runs', p['id'])['recovery_error'], 'offline')
    def test_artifact_ids_cannot_escape_state_directory(self):
        with self.assertRaises(HarnessError):
            self.h.load('runs', '../../secret')
    def test_mcp_contract_and_unknown_tool(self):
        self.assertEqual(len(dispatch({'method': 'tools/list'})['tools']), 6)
        self.assertEqual(dispatch({'method': 'initialize', 'params': {'protocolVersion': '2024-11-05'}})['protocolVersion'], '2024-11-05')
        with self.assertRaises(ValueError):
            dispatch({'method': 'tools/call', 'params': {'name': 'shell'}})
    def test_invalid_workspace_schemes_and_tokens_are_rejected(self):
        base = json.loads(Path('config/launcher.json').read_text())
        for target in ('javascript:alert(1)', 'file:///tmp/a', 'https://user:secret@example.com'):
            cfg = copy.deepcopy(base)
            cfg['jarvis']['url'] = target
            profile = Path(self.temp.name) / 'profile.json'
            profile.write_text(json.dumps(cfg))
            with self.assertRaises(HarnessError):
                configure_launcher(profile)

if __name__ == '__main__':
    unittest.main()
