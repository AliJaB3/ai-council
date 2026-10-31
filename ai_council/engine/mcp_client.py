"""Minimal stdio MCP client with a default-deny tool policy."""
import json
import re
import shlex
import subprocess
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict
    is_mutating: bool


class MCPClient:
    def __init__(self, command=None, allow_mutating=False):
        self.command = shlex.split(command) if isinstance(command, str) else command
        self.allow_mutating = allow_mutating
        self.process = None
        self._id = 0
        self._lock = threading.Lock()
        self._tools = {}

    @staticmethod
    def classify_tool(name):
        words = re.findall(r'[a-z]+', re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower())
        mutating = {'set', 'write', 'create', 'delete', 'exec', 'update', 'remove', 'run', 'modify', 'send', 'post', 'put', 'patch'}
        readonly = {'query', 'get', 'read', 'list', 'search'}
        return bool(mutating.intersection(words)) or not bool(readonly.intersection(words))

    def connect(self):
        if not self.command:
            raise ValueError('MCP server command is required')
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        try:
            self._request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'ai-council', 'version': '7.1'}})
            self._send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        except BaseException:
            self.close()
            raise
        return self

    def _send(self, message):
        if self.process is None or self.process.stdin is None:
            raise RuntimeError('MCP client is not connected')
        self.process.stdin.write(json.dumps(message) + '\n')
        self.process.stdin.flush()

    def _request(self, method, params=None):
        with self._lock:
            self._id += 1
            request_id = self._id
            self._send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params or {}})
            while True:
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError('MCP server closed its output')
                response = json.loads(line)
                if response.get('jsonrpc') != '2.0':
                    raise ValueError('invalid JSON-RPC response')
                if response.get('id') != request_id:
                    continue
                if 'error' in response:
                    raise RuntimeError('MCP error: ' + str(response['error']))
                if 'result' not in response:
                    raise ValueError('missing JSON-RPC result')
                return response['result']

    def list_tools(self):
        tools = []
        cursor = None
        while True:
            result = self._request('tools/list', {'cursor': cursor} if cursor else {})
            for item in result.get('tools', []):
                tool = MCPTool(item['name'], item.get('description', ''), item.get('inputSchema', {}), self.classify_tool(item['name']))
                tools.append(tool)
            cursor = result.get('nextCursor')
            if not cursor:
                break
        self._tools = {tool.name: tool for tool in tools}
        return tools

    def call_tool(self, name, arguments=None, allow_mutating=False):
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError('unknown MCP tool: ' + name)
        if tool.is_mutating and not (allow_mutating or self.allow_mutating):
            raise PermissionError('mutating MCP tool requires explicit permission: ' + name)
        return self._request('tools/call', {'name': name, 'arguments': arguments or {}})

    def close(self):
        if self.process is not None:
            process, self.process = self.process, None
            if process.stdin:
                process.stdin.close()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()
