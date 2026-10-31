"""Read-only boundary for untrusted MCP evidence."""
import json
import time
from uuid import uuid4
from ..contracts import EvidenceEnvelope

class EvidenceGateway:
    def __init__(self, client):
        self.client = client

    def call_tool(self, tool_name, args=None):
        tools = self.client.list_tools()
        tool = next((item for item in tools if item.name == tool_name), None)
        if tool is None:
            raise ValueError('unknown MCP tool: ' + tool_name)
        if tool.is_mutating:
            raise PermissionError('mutating MCP tool forbidden: ' + tool_name)
        result = self.client.call_tool(tool_name, args or {})
        content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, sort_keys=True)
        return EvidenceEnvelope(str(uuid4()), 'mcp://' + tool_name, content, timestamp=time.time())
