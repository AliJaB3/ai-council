"""Static policy and resource-limited subprocess for generated Python templates.

This gate is defense in depth, not an operating-system security boundary.
"""
import ast
import subprocess
import sys


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
    def __init__(self, timeout: float = 5.0, memory_limit: int = 256 * 1024 * 1024):
        self.timeout = timeout
        self.memory_limit = memory_limit

    def run(self, code: str):
        ASTSecurityGate().validate(code)
        # Set limits in the child interpreter; never hold a parent lock during execution.
        bootstrap = ('import resource, sys\n'
                     'limit = int(sys.argv[1])\n'
                     'resource.setrlimit(resource.RLIMIT_AS, (limit, limit))\n'
                     'exec(compile(sys.stdin.read(), "<sandbox>", "exec"))\n')
        return subprocess.run([sys.executable, '-I', '-c', bootstrap, str(self.memory_limit)],
                              input=code, text=True, capture_output=True, timeout=self.timeout, check=False)
