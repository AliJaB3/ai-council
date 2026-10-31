"""Interpret counterexample execution without executing code in process."""
from enum import Enum
import re

class FalsificationOutcome(str, Enum):
    REFUTED = 'REFUTED'
    NOT_REFUTED = 'NOT_REFUTED'
    INCONCLUSIVE = 'INCONCLUSIVE'
    EXECUTION_ERROR = 'EXECUTION_ERROR'

class CounterExampleHarness:
    def evaluate_objection(self, objection, sandbox_runner):
        if not objection.counter_code.strip():
            return FalsificationOutcome.INCONCLUSIVE, 'No code'
        try:
            result = sandbox_runner.run(objection.counter_code)
        except Exception as exc:
            return FalsificationOutcome.EXECUTION_ERROR, str(exc)
        output = (result.stdout or '') + (result.stderr or '')
        if result.returncode == 0:
            return FalsificationOutcome.REFUTED, output
        if re.search(r'(?m)^AssertionError(?::.*)?\s*$', result.stderr or ''):
            return FalsificationOutcome.NOT_REFUTED, output
        return FalsificationOutcome.EXECUTION_ERROR, output
