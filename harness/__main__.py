import argparse
import json
import shutil
import sys
from pathlib import Path
from .core import Adb, Harness, HarnessError, configure_launcher


def main():
    p = argparse.ArgumentParser(description='Android TV Harness — explicit TV actions with saved evidence')
    p.add_argument('--serial', help='One paired ADB serial or host:port; never inferred')
    p.add_argument('--state-dir', help='Private evidence directory; defaults to .state')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    sub.add_parser('inventory')
    sub.add_parser('screenshot')
    plan = sub.add_parser('plan')
    plan.add_argument('request', help='JSON request file: disable, enable, apk, set_home')
    for name in ('apply', 'restore', 'run'):
        cmd = sub.add_parser(name)
        cmd.add_argument('id')
    cfg = sub.add_parser('configure')
    cfg.add_argument('profile')
    sub.add_parser('mcp')
    args = p.parse_args()
    try:
        if args.command == 'doctor':
            result = {'status': 'ready' if shutil.which('adb') else 'missing_dependency',
                      'adb': shutil.which('adb'), 'apkanalyzer': shutil.which('apkanalyzer'),
                      'hermes': 'not_configured', 'device_mutated': False}
        elif args.command == 'configure':
            result = configure_launcher(args.profile)
        elif args.command == 'mcp':
            from .mcp import serve
            serve(args.state_dir)
            return
        else:
            h = Harness(Adb(args.serial) if args.serial else None, args.state_dir)
            if args.command == 'run':
                result = h.load('runs', args.id)
            elif args.command == 'plan':
                result = h.plan(json.loads(Path(args.request).read_text()))
            elif args.command in ('apply', 'restore'):
                result = getattr(h, args.command)(args.id)
            else:
                result = getattr(h, args.command)()
        print(json.dumps(result, indent=2))
        if result.get('status') in ('failed', 'failed_rolled_back', 'recovery_required', 'missing_dependency'):
            sys.exit(1)
    except (HarnessError, OSError, ValueError, IndexError) as e:
        print(json.dumps({'status': 'failed', 'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()
