from __future__ import annotations
import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HOME = 'com.gathin.tvhome/.MainActivity'
PKG = 'com.gathin.tvhome'
PACKAGE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+$')
COMPONENT = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.]+/[a-zA-Z0-9_.$]+$')
# Preserve core OS, settings, input, app store, Cast, voice, updates and tuners by default.
PROTECTED = ('android', 'com.android.', 'com.google.android.gms', 'com.google.android.gsf',
             'com.android.vending', 'com.google.android.inputmethod.', 'com.google.android.tv',
             'com.google.android.katniss', 'com.google.android.apps.tv.launcherx',
             'com.google.android.apps.mediashell', 'com.gathin.tvhome')
RISK = re.compile(r'(launcher|inputmethod|keyboard|update|ota|cast|mediashell|tuner|tvcenter|assistant)', re.I)

class HarnessError(Exception):
    pass


def package(value):
    if not isinstance(value, str) or not PACKAGE.fullmatch(value):
        raise HarnessError('Invalid Android package name')
    return value


def canonical_component(value):
    if not COMPONENT.fullmatch(value):
        return value
    pkg, activity = value.split('/', 1)
    return pkg + '/' + (pkg + activity if activity.startswith('.') else activity)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.chmod(0o600)
    os.replace(temp, path)


class Adb:
    """Native ADB supports both paired Android 14 TLS and older TCP devices.

    Connections/pairing are explicit operator operations, never network discovery.
    """
    def __init__(self, serial, executable='adb'):
        if not isinstance(serial, str) or not re.fullmatch(r'[a-zA-Z0-9_.:\[\]-]{1,160}', serial):
            raise HarnessError('Provide one explicit ADB serial or host:port')
        self.serial = serial
        self.executable = executable

    def run(self, *args, timeout=30, binary=False):
        try:
            p = subprocess.run([self.executable, '-s', self.serial, *args],
                               capture_output=True, timeout=timeout)
        except FileNotFoundError as e:
            raise HarnessError('ADB is missing. Install Android platform-tools.') from e
        except subprocess.TimeoutExpired as e:
            raise HarnessError('ADB timed out; inspect device state before retrying writes') from e
        if p.returncode:
            raise HarnessError(p.stderr.decode(errors='replace').strip()[:1000] or 'ADB failed')
        return p.stdout if binary else p.stdout.decode(errors='replace').strip()

    def shell(self, *args):
        # Android shell failures do not always propagate through adb. Check a private exit marker.
        command = shlex.join(str(a) for a in args)
        out = self.run('shell', command + '; r=$?; printf "\\n__TVH_EXIT__%s\\n" "$r"')
        match = re.search(r'(?:^|\n)__TVH_EXIT__(\d+)\s*$', out)
        if not match or match[1] != '0':
            raise HarnessError('TV command failed: ' + out[:1000])
        return out[:match.start()].strip()


class Harness:
    def __init__(self, transport=None, state_dir=None):
        self.adb = transport
        self.state = Path(state_dir or os.environ.get('TV_HARNESS_STATE', ROOT / '.state'))

    @contextlib.contextmanager
    def lock(self):
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        # macOS/Linux advisory lock releases on crashes; persisted journals retain recovery state.
        import fcntl
        with (self.state / 'runtime.lock').open('a') as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise HarnessError('Another harness operation is active') from e
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def path(self, kind, ident):
        if not isinstance(ident, str) or not re.fullmatch(r'[0-9a-f]{32}', ident):
            raise HarnessError('Invalid artifact ID')
        return self.state / kind / (ident + '.json')

    def load(self, kind, ident):
        try:
            return json.loads(self.path(kind, ident).read_text())
        except (OSError, ValueError) as e:
            raise HarnessError('Artifact not found or invalid') from e

    def shell(self, *args):
        if self.adb is None:
            raise HarnessError('This operation needs an explicit device target')
        return self.adb.shell(*args)

    def inventory(self):
        props = {p: self.shell('getprop', p) for p in (
            'ro.product.manufacturer', 'ro.product.model', 'ro.product.device',
            'ro.build.version.release', 'ro.build.version.sdk', 'ro.build.fingerprint', 'ro.serialno')}
        if not props['ro.build.fingerprint']:
            raise HarnessError('Device identity unavailable')
        features = self.shell('pm', 'list', 'features')
        if 'android.software.leanback' not in features and 'android.hardware.type.television' not in features:
            raise HarnessError('Target does not advertise Android TV features')
        packages = sorted(line[8:] for line in self.shell('pm', 'list', 'packages', '--user', '0').splitlines()
                          if line.startswith('package:'))
        disabled = sorted(line[8:] for line in self.shell('pm', 'list', 'packages', '-d', '--user', '0').splitlines()
                          if line.startswith('package:'))
        resolved = self.shell('cmd', 'package', 'resolve-activity', '--brief', '--user', '0',
                              '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.HOME').splitlines()
        home = resolved[-1] if resolved else ''
        return {'serial': self.adb.serial, 'identity': digest(props), 'properties': props,
                'packages': packages, 'disabled': disabled, 'home': home,
                'observed_at': time.time(), 'user': 0}

    def enabled_state(self, pkg):
        dump = self.shell('dumpsys', 'package', pkg)
        match = re.search(r'User 0:([^\n]*)', dump)
        enabled = re.search(r'\benabled=(\d+)\b', match[1]) if match else None
        if not enabled or enabled[1] not in ('0', '1', '2', '3', '4'):
            raise HarnessError('Cannot snapshot exact user-0 state for ' + pkg)
        return int(enabled[1])

    def plan(self, request):
        with self.lock():
            return self._plan(request)

    def _plan(self, request):
        if not isinstance(request, dict) or set(request) - {'disable', 'enable', 'apk', 'set_home'}:
            raise HarnessError('Allowed request fields: disable, enable, apk, set_home')
        for field in ('disable', 'enable'):
            if not isinstance(request.get(field, []), list) or len(request.get(field, [])) > 30:
                raise HarnessError(field + ' must be a list of at most 30 packages')
        if 'set_home' in request and not isinstance(request['set_home'], bool):
            raise HarnessError('set_home must be boolean')
        inv = self.inventory()
        if not COMPONENT.fullmatch(inv['home']):
            raise HarnessError('Resolve the stock Home selection before planning changes')
        disable = [package(p) for p in request.get('disable', [])]
        enable = [package(p) for p in request.get('enable', [])]
        if len(set(disable + enable)) != len(disable + enable):
            raise HarnessError('Repeated or contradictory package changes')
        for p in disable:
            if p.startswith(PROTECTED) or RISK.search(p) or p == inv['home'].split('/')[0]:
                raise HarnessError('Protected TV capability cannot be disabled: ' + p)
        for p in disable + enable:
            if p not in inv['packages']:
                raise HarnessError('Package is absent: ' + p)
        steps = []
        before = {p: self.enabled_state(p) for p in disable + enable}
        apk = request.get('apk')
        if apk:
            if PKG in inv['packages']:
                raise HarnessError('Launcher already installed; in-place APK updates need a separate backup workflow')
            path = Path(apk).expanduser().resolve()
            if path.suffix != '.apk' or not path.is_file():
                raise HarnessError('APK file not found')
            apkanalyzer = shutil.which('apkanalyzer')
            if not apkanalyzer:
                raise HarnessError('apkanalyzer is required to verify the launcher APK before installation')
            environment = os.environ.copy()
            local_jdk = Path('/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home')
            if not environment.get('JAVA_HOME') and local_jdk.is_dir():
                environment['JAVA_HOME'] = str(local_jdk)
            result = subprocess.run([apkanalyzer, 'manifest', 'application-id', str(path)],
                                    capture_output=True, text=True, timeout=30, env=environment)
            if result.returncode or result.stdout.strip() != PKG:
                raise HarnessError('Only the com.gathin.tvhome launcher APK is allowed')
            steps.append({'action': 'install', 'apk': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for p in enable:
            steps.append({'action': 'enable', 'package': p})
        if request.get('set_home'):
            if not apk and (PKG not in inv['packages'] or PKG in inv['disabled']):
                raise HarnessError('Install or enable the launcher before selecting it as Home')
            steps.append({'action': 'home', 'component': HOME})
        for p in disable:
            steps.append({'action': 'disable', 'package': p})
        if not steps:
            raise HarnessError('Request contains no changes')
        plan = {'id': uuid.uuid4().hex, 'created_at': time.time(), 'expires_at': time.time() + 900,
                'inventory': inv, 'before': before, 'steps': steps, 'request': request,
                'scope': 'Android TV user 0; retain stock launcher, Cast, voice, keyboard and updates'}
        plan['integrity'] = digest(plan)
        save(self.path('plans', plan['id']), plan)
        return plan

    def _valid_plan(self, ident):
        p = self.load('plans', ident)
        claimed = p.pop('integrity', None)
        if digest(p) != claimed:
            raise HarnessError('Plan integrity check failed')
        p['integrity'] = claimed
        if p['expires_at'] < time.time():
            raise HarnessError('Plan expired; create a fresh plan')
        return p

    def apply(self, ident):
        with self.lock():
            for existing in (self.state / 'runs').glob('*.json'):
                record = json.loads(existing.read_text())
                if record.get('status') in ('running', 'failed', 'restoring', 'recovery_required'):
                    raise HarnessError('An unfinished run requires recovery before new writes: ' + record['id'])
            p = self._valid_plan(ident)
            runpath = self.path('runs', ident)
            if runpath.exists():
                raise HarnessError('Plan already attempted; inspect its run or restore it')
            inv = self.inventory()
            for key in ('serial', 'identity', 'home', 'packages', 'disabled'):
                if inv[key] != p['inventory'][key]:
                    raise HarnessError('Device state changed; create a fresh plan')
            for pkg, value in p['before'].items():
                if self.enabled_state(pkg) != value:
                    raise HarnessError('Package state changed; create a fresh plan')
            for step in p['steps']:
                if step['action'] == 'install' and hashlib.sha256(Path(step['apk']).read_bytes()).hexdigest() != step['sha256']:
                    raise HarnessError('APK changed after planning')
            run = {'id': ident, 'status': 'running', 'started_at': time.time(), 'plan': p,
                   'attempted': [], 'verified': [], 'recovery': []}
            save(runpath, run)
            try:
                for step in p['steps']:
                    # Persist intent BEFORE a write, including ambiguous timeout/crash outcomes.
                    run['attempted'].append(step)
                    save(runpath, run)
                    self.execute(step)
                    run['verified'].append(step)
                    save(runpath, run)
                run['status'] = 'completed'
                run['after'] = self.inventory()
            except Exception as e:
                run['error'] = str(e)[:1000]
                run['status'] = 'failed'
                save(runpath, run)
                self._restore(run)
            run['finished_at'] = time.time()
            save(runpath, run)
            return run

    def execute(self, step):
        action = step['action']
        if action in ('disable', 'enable'):
            command = 'disable-user' if action == 'disable' else 'enable'
            self.shell('pm', command, '--user', '0', step['package'])
            expected = 3 if action == 'disable' else 1
            if self.enabled_state(step['package']) != expected:
                raise HarnessError('Package change verification failed')
        elif action == 'install':
            out = self.adb.run('install', '--user', '0', step['apk'], timeout=180)
            if 'Success' not in out or PKG not in self.inventory()['packages']:
                raise HarnessError('Launcher installation not verified')
        elif action == 'home':
            self.shell('cmd', 'package', 'set-home-activity', '--user', '0', step['component'])
            actual_home = self.inventory()['home']
            if canonical_component(actual_home) != canonical_component(HOME):
                raise HarnessError('Home selection not verified: ' + actual_home)
            self.shell('am', 'start', '-W', '-n', HOME)
            self.shell('input', 'keyevent', 'KEYCODE_HOME')
            resumed = self.shell('dumpsys', 'activity', 'activities')
            if not re.search(r'(?:mResumedActivity|topResumedActivity)[^\n]*com\.gathin\.tvhome', resumed):
                raise HarnessError('Launcher is not the foreground activity')
        else:
            raise HarnessError('Unregistered action')

    def restore(self, ident):
        with self.lock():
            run = self.load('runs', ident)
            if run['status'] in ('restored', 'failed_rolled_back'):
                return run
            self._restore(run)
            save(self.path('runs', ident), run)
            return run

    def _restore(self, run):
        p = run['plan']
        try:
            inv = self.inventory()
        except Exception as e:
            run['status'] = 'recovery_required'
            run['recovery_error'] = str(e)[:1000]
            save(self.path('runs', run['id']), run)
            return
        if inv['identity'] != p['inventory']['identity'] or inv['serial'] != p['inventory']['serial']:
            run['status'] = 'recovery_required'
            run['recovery_error'] = 'Recovery target does not match original device'
            return
        run['status'] = 'restoring'
        save(self.path('runs', run['id']), run)
        try:
            attempted = run['attempted']
            for pkg, enabled in p['before'].items():
                if any(s.get('package') == pkg for s in attempted):
                    cmd = {0: 'default-state', 1: 'enable', 2: 'disable', 3: 'disable-user', 4: 'disable-until-used'}[enabled]
                    self.shell('pm', cmd, '--user', '0', pkg)
                    if self.enabled_state(pkg) != enabled:
                        raise HarnessError('Restore verification failed for ' + pkg)
                    run['recovery'].append({'package': pkg, 'restored_state': enabled})
                    save(self.path('runs', run['id']), run)
            if any(s['action'] == 'home' for s in attempted):
                old_home = p['inventory']['home']
                self.shell('cmd', 'package', 'set-home-activity', '--user', '0', old_home)
                if canonical_component(self.inventory()['home']) != canonical_component(old_home):
                    raise HarnessError('Original Home restoration not verified')
                self.shell('input', 'keyevent', 'KEYCODE_HOME')
            if any(s['action'] == 'install' for s in attempted) and PKG in self.inventory()['packages']:
                self.adb.run('uninstall', '--user', '0', PKG, timeout=60)
                if PKG in self.inventory()['packages']:
                    raise HarnessError('New launcher removal not verified')
            run['status'] = 'failed_rolled_back' if 'error' in run else 'restored'
            run['after_restore'] = self.inventory()
        except Exception as e:
            run['status'] = 'recovery_required'
            run['recovery_error'] = str(e)[:1000]
        save(self.path('runs', run['id']), run)

    def screenshot(self):
        with self.lock():
            self.inventory()  # Verify explicit TV target before capturing.
            ident = uuid.uuid4().hex
            data = self.adb.run('exec-out', 'screencap', '-p', binary=True)
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                raise HarnessError('TV returned no valid PNG; HDMI/Live TV may prevent capture')
            dest = self.state / 'screenshots' / (ident + '.png')
            dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            dest.write_bytes(data)
            dest.chmod(0o600)
            return {'status': 'completed', 'artifact': str(dest), 'sha256': hashlib.sha256(data).hexdigest()}


def configure_launcher(config_path):
    """Validate the profile and configure only source resources; no device effects."""
    cfg = json.loads(Path(config_path).read_text())
    allowed = {'dock_apps', 'hidden_apps', 'live_tv_package', 'columns', 'jarvis'}
    if set(cfg) - allowed:
        raise HarnessError('Unknown launcher profile field')
    for field in ('dock_apps', 'hidden_apps'):
        if not isinstance(cfg.get(field), list) or len(cfg[field]) > 50:
            raise HarnessError(field + ' must be a package list')
        for p in cfg[field]:
            package(p)
    if cfg.get('live_tv_package'):
        package(cfg['live_tv_package'])
    if type(cfg.get('columns')) is not int or not 1 <= cfg['columns'] <= 6:
        raise HarnessError('Columns must be between 1 and 6')
    jarvis = cfg.get('jarvis', {})
    if not isinstance(jarvis, dict) or set(jarvis) - {'label', 'url', 'package'}:
        raise HarnessError('Jarvis fields: label, url, package')
    label = jarvis.get('label', '@J.A.R.V.I.S.')
    if label not in ('@J.A.R.V.I.S.', 'Hermes'):
        raise HarnessError('Button label must be @J.A.R.V.I.S. or Hermes')
    url, target = jarvis.get('url', ''), jarvis.get('package', '')
    if not isinstance(url, str) or not isinstance(target, str) or (url and target):
        raise HarnessError('Choose either a workspace URL or an app package')
    if target:
        package(target)
    if url:
        from urllib.parse import urlsplit
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
            raise HarnessError('Workspace must be an HTTP(S) address without credentials')
    tree = ET.Element('resources')
    for field in ('dock_apps', 'hidden_apps'):
        el = ET.SubElement(tree, 'string-array', name=field)
        for p in cfg[field]:
            ET.SubElement(el, 'item').text = p
    ET.SubElement(tree, 'integer', name='columns').text = str(cfg['columns'])
    for key, val in {'live_tv_package': cfg.get('live_tv_package', ''), 'jarvis_label': label,
                     'jarvis_url': url, 'jarvis_package': target}.items():
        # Android string resources treat apostrophes and @ specially.
        el = ET.SubElement(tree, 'string', name=key, translatable='false')
        el.text = '"' + val.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'") + '"'
    ET.indent(tree)
    dest = ROOT / 'launcher/app/src/main/res/values/config.xml'
    ET.ElementTree(tree).write(dest, encoding='utf-8', xml_declaration=True)
    return {'status': 'completed', 'resource': str(dest), 'button_label': label,
            'connection_configured': bool(url or target)}
