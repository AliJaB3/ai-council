"""Static policy and resource-limited subprocess for generated Python templates.

This gate is defense in depth, not an operating-system security boundary.
"""
import ast
import os
import math
import resource
import subprocess
import sys


def apply_resource_limits(max_memory_mb: int = 512, max_cpu_s: int = 5):
    for kind, limit in (("RLIMIT_AS", max_memory_mb * 1024 * 1024), ("RLIMIT_CPU", max_cpu_s)):
        if hasattr(resource, kind):
            resource.setrlimit(getattr(resource, kind), (limit, limit))


def sanitize_env() -> dict:
    blocked = ("KEY", "TOKEN", "SECRET", "PASSWORD", "AUTH", "PROXY")
    return {key: value for key, value in os.environ.items()
            if not any(part in key.upper() for part in blocked)}


class ASTPolicyViolation(RuntimeError):
    pass


class ASTSecurityGate(ast.NodeVisitor):
    forbidden_modules = frozenset({'os', 'sys', 'subprocess', 'socket', 'shutil', 'urllib', 'requests'})
    forbidden_calls = frozenset({'eval', 'exec', 'open', 'compile', 'getattr', 'setattr', '__import__'})

    def validate(self, code: str):
        tree = ast.parse(code)
        self.visit(tree)
        return tree

    def visit_Import(self, node):
        if any(alias.name.split('.')[0] in self.forbidden_modules for alias in node.names):
            raise ASTPolicyViolation('Forbidden import')
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in self.forbidden_modules:
            raise ASTPolicyViolation('Forbidden import')
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.forbidden_calls:
            raise ASTPolicyViolation('Forbidden call: ' + node.func.id)
        if isinstance(node.func, ast.Attribute) and node.func.attr in self.forbidden_calls:
            raise ASTPolicyViolation('Forbidden call: ' + node.func.attr)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith('__') and node.attr.endswith('__'):
            raise ASTPolicyViolation('Dunder attribute access is forbidden')
        self.generic_visit(node)


class IsolatedSandboxRunner:
    def __init__(self, timeout: float = 15.0, memory_limit: int = 256 * 1024 * 1024):
        self.timeout = timeout
        self.memory_limit = memory_limit

    def run(self, code: str):
        ASTSecurityGate().validate(code)
        return subprocess.run([sys.executable, '-I', '-c', code],
                              text=True, capture_output=True, timeout=self.timeout, check=False,
                              env=sanitize_env(),
                              preexec_fn=lambda: apply_resource_limits(
                                  max(1, self.memory_limit // (1024 * 1024)),
                                  max(1, math.ceil(self.timeout))))
