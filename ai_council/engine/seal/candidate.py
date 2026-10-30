"""Create patches only for explicitly allowed, ordinary workspace files."""
import difflib
import hashlib
from pathlib import Path

class CandidateGenerator:
    def __init__(self, workspace, targets):
        self.workspace = Path(workspace).resolve()
        self.targets = {self._check(path) for path in targets}
    def _check(self, path):
        raw = Path(path)
        if raw.is_absolute() or '..' in raw.parts: raise ValueError('target must be relative to workspace')
        if any(part.lower() in {'.git', '.github', '.gitlab', '.agents', '.codex', 'tests', 'test', 'security'} for part in raw.parts): raise ValueError('protected path')
        name = raw.name.lower()
        if name.startswith('test_') or name.endswith('_test.py') or name in {'pyproject.toml', 'setup.cfg', 'tox.ini', 'pytest.ini', 'conftest.py', 'dockerfile', '.env'} or 'security' in name: raise ValueError('protected file')
        full = self.workspace / raw
        if any((self.workspace.joinpath(*raw.parts[:i])).is_symlink() for i in range(1, len(raw.parts) + 1)): raise ValueError('symlink target')
        if not full.resolve().is_relative_to(self.workspace) or not full.is_file(): raise ValueError('invalid target')
        return raw.as_posix()
    def generate(self, changes):
        if not changes: raise ValueError('empty candidate')
        parts = []
        for path, content in changes.items():
            path = self._check(path)
            if path not in self.targets: raise ValueError('target not authorized')
            if not isinstance(content, str): raise ValueError('content must be text')
            original = (self.workspace / path).read_text()
            parts.extend(difflib.unified_diff(original.splitlines(keepends=True), content.splitlines(keepends=True), fromfile='a/'+path, tofile='b/'+path))
        patch = ''.join(parts)
        if not patch: raise ValueError('candidate has no changes')
        return patch
    @staticmethod
    def digest(patch): return hashlib.sha256(patch.encode()).hexdigest()
