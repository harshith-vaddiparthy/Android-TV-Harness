"""Optional stdio MCP adapter. No HTTP listener, model configuration or arbitrary shell tool."""
import json
import sys
from .core import Adb, Harness


def schema(properties, required):
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}

SERIAL = {'type': 'string', 'description': 'Explicit paired Android TV ADB serial or host:port'}
ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$'}
REQUEST = schema({'disable': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 30},
                  'enable': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 30},
                  'apk': {'type': 'string'}, 'set_home': {'type': 'boolean'}}, [])
TOOLS = [
    {'name': 'tv_inventory', 'description': 'Read Android TV user-0 identity, packages and current Home.',
     'inputSchema': schema({'serial': SERIAL}, ['serial'])},
    {'name': 'tv_plan', 'description': 'Read-only on TV. Save a 15-minute change plan and exact recovery snapshot.',
     'inputSchema': schema({'serial': SERIAL, 'request': REQUEST}, ['serial', 'request'])},
    {'name': 'tv_apply', 'description': 'WRITE: execute a reviewed plan ID. Caller must have user authorization for its exact changes.',
     'inputSchema': schema({'serial': SERIAL, 'id': ID}, ['serial', 'id'])},
    {'name': 'tv_restore', 'description': 'WRITE: restore original package states/Home from a recorded run.',
     'inputSchema': schema({'serial': SERIAL, 'id': ID}, ['serial', 'id'])},
    {'name': 'tv_run', 'description': 'Read persisted execution and recovery evidence.',
     'inputSchema': schema({'id': ID}, ['id'])},
    {'name': 'tv_screenshot', 'description': 'Read the current TV framebuffer into a private local PNG artifact.',
     'inputSchema': schema({'serial': SERIAL}, ['serial'])},
]


def dispatch(msg, state_dir=None):
    method, args = msg.get('method'), msg.get('params', {})
    if method == 'initialize':
        versions = ('2024-11-05', '2025-03-26', '2025-06-18')
        version = args.get('protocolVersion')
        return {'protocolVersion': version if version in versions else versions[-1],
                'capabilities': {'tools': {}}, 'serverInfo': {'name': 'android-tv-harness', 'version': '1.0.0'}}
    if method == 'ping':
        return {}
    if method == 'tools/list':
        return {'tools': TOOLS}
    if method != 'tools/call':
        raise ValueError('Unsupported method')
    name, a = args.get('name'), args.get('arguments', {})
    tool = next((t for t in TOOLS if t['name'] == name), None)
    if tool is None:
        raise ValueError('Unknown tool')
    spec = tool['inputSchema']
    if not isinstance(a, dict) or set(a) - set(spec['properties']) or not set(spec['required']) <= set(a):
        raise ValueError('Invalid tool arguments')
    h = Harness(Adb(a['serial']) if 'serial' in a else None, state_dir)
    if name == 'tv_plan':
        result = h.plan(a['request'])
    elif name == 'tv_run':
        result = h.load('runs', a['id'])
    elif name in ('tv_apply', 'tv_restore'):
        result = getattr(h, name[3:])(a['id'])
    else:
        result = getattr(h, name[3:])()
    return {'content': [{'type': 'text', 'text': json.dumps(result)}],
            'isError': result.get('status') in ('failed', 'failed_rolled_back', 'recovery_required')}


def serve(state_dir=None):
    for line in sys.stdin:
        msg = None
        try:
            if len(line) > 1_048_576:
                raise ValueError('Message too large')
            msg = json.loads(line)
            if not isinstance(msg, dict):
                raise ValueError('JSON-RPC message must be an object')
            if 'id' not in msg:  # notifications never perform tools or produce responses
                continue
            result = dispatch(msg, state_dir)
            response = {'jsonrpc': '2.0', 'id': msg['id'], 'result': result}
        except Exception as e:
            if isinstance(msg, dict) and msg.get('method') == 'tools/call':
                response = {'jsonrpc': '2.0', 'id': msg.get('id'), 'result': {
                    'content': [{'type': 'text', 'text': json.dumps({'status': 'failed', 'error': str(e)[:1000]})}],
                    'isError': True}}
            else:
                response = {'jsonrpc': '2.0', 'id': msg.get('id') if isinstance(msg, dict) else None,
                            'error': {'code': -32600, 'message': str(e)[:1000]}}
        print(json.dumps(response), flush=True)
