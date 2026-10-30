"""Bubblewrap sandbox. Fail closed if the OS isolation backend is unavailable."""
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tempfile

class IsolatedSandboxRunner:
    def __init__(self, workspace, timeout=30, memory_limit=1024*1024*1024):
        self.workspace = Path(workspace).resolve(); self.timeout = timeout; self.memory_limit = memory_limit
    def run(self, command, changes=None):
        bwrap = shutil.which('bwrap')
        if not bwrap: return {'status': 'FAILED', 'error': 'bubblewrap isolation unavailable'}
        if not isinstance(command, (list, tuple)) or not command: return {'status': 'FAILED', 'error': 'command must be an argument list'}
        try:
            with tempfile.TemporaryDirectory(prefix='seal-') as temp:
                work = Path(temp) / 'workspace'
                shutil.copytree(self.workspace, work, symlinks=True, ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
                if changes:
                    from .candidate import CandidateGenerator
                    generator = CandidateGenerator(work, changes.keys())
                    generator.generate(changes)
                    for path, content in changes.items(): (work / path).write_text(content)
                args = [bwrap, '--die-with-parent', '--new-session', '--unshare-all', '--ro-bind', '/', '/', '--bind', str(work), '/workspace', '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev', '--chdir', '/workspace', '--clearenv', '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin', '--setenv', 'HOME', '/tmp', '--'] + list(command)
                def limits():
                    resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit, self.memory_limit))
                    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, preexec_fn=limits)
                try: stdout, stderr = process.communicate(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.communicate()
                    return {'status': 'FAILED', 'error': 'timeout'}
                return {'status': 'PASSED' if process.returncode == 0 else 'FAILED', 'returncode': process.returncode, 'stdout': stdout.decode(errors='replace')[-10000:], 'stderr': stderr.decode(errors='replace')[-10000:]}
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return {'status': 'FAILED', 'error': str(exc)}
