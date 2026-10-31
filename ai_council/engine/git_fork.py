"""Execute candidate tests in a disposable Git worktree.

A worktree isolates files, not processes or network access. Only run trusted test commands.
"""
from dataclasses import dataclass
from pathlib import Path
import shlex
import os
import signal
import subprocess
import tempfile
import time
from uuid import uuid4
from .sandbox_runner import ASTSecurityGate, ASTPolicyViolation


@dataclass
class ExecutionReceipt:
    correlation_id: str
    branch_name: str
    status: str
    exit_code: int
    stdout: str
    duration_ms: float


class CounterfactualForkManager:
    def fork_and_test(self, repo_path, patch_dict, test_command, correlation_id, timeout_s=20.0):
        start = time.monotonic()
        branch = 'council/fork-' + uuid4().hex
        status, code, output = 'FAILED', -1, ''
        def receipt():
            return ExecutionReceipt(correlation_id, branch, status, code, output, (time.monotonic()-start)*1000)
        try:
            if timeout_s <= 0 or not patch_dict or not isinstance(patch_dict, dict):
                raise ValueError('patch and positive timeout required')
            for name, content in patch_dict.items():
                path = Path(name)
                if not isinstance(name, str) or not isinstance(content, str) or path.is_absolute() or '..' in path.parts or '.git' in path.parts:
                    raise ValueError('invalid patch path or contents')
                if path.suffix == '.py':
                    ASTSecurityGate().validate(content)
        except (ValueError, TypeError, SyntaxError, ASTPolicyViolation) as exc:
            status, output = 'SECURITY_VIOLATION', str(exc)
            return receipt()
        repo = str(Path(repo_path).resolve())
        with tempfile.TemporaryDirectory(prefix='council-fork-') as temp:
            worktree = Path(temp) / 'worktree'
            added = False
            try:
                subprocess.run(['git', '-C', repo, 'worktree', 'add', '-b', branch, str(worktree), 'HEAD'], check=True, capture_output=True, text=True, timeout=timeout_s)
                added = True
                for name, content in patch_dict.items():
                    target = worktree / name
                    if not target.resolve().is_relative_to(worktree.resolve()):
                        raise ValueError('patch path escapes worktree')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding='utf-8')
                command = shlex.split(test_command) if isinstance(test_command, str) else list(test_command)
                if not command:
                    raise ValueError('test command is required')
                process = subprocess.Popen(command, cwd=worktree, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, stderr = process.communicate(timeout=timeout_s)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                    raise subprocess.TimeoutExpired(command, timeout_s, output=stdout, stderr=stderr)
                code, output = process.returncode, stdout + stderr
                status = 'PASSED' if code == 0 else 'FAILED'
            except (subprocess.SubprocessError, OSError, ValueError) as exc:
                output = str(exc)
                if isinstance(exc, subprocess.CalledProcessError):
                    output += '\n' + (exc.stderr or '')
            finally:
                if added:
                    subprocess.run(['git', '-C', repo, 'worktree', 'remove', '--force', str(worktree)], capture_output=True, text=True)
                subprocess.run(['git', '-C', repo, 'branch', '-D', branch], capture_output=True, text=True)
        return receipt()
