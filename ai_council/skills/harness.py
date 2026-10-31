"""Static pre-flight checks and regression-result aggregation.

These checks are heuristics, not a substitute for isolation or a security review.
"""
import hashlib
import math
import re
from .models import Domain


class PreFlightHarness:
    def __init__(self, domain=Domain.GENERAL):
        self.domain = Domain(domain)
        self._cache = {}

    def verify_candidate(self, candidate_code: str, test_runner_fn=None) -> dict:
        digest = hashlib.sha256(candidate_code.encode('utf-8')).digest()
        key = (digest, self.domain, id(test_runner_fn))
        cached = self._cache.get(key)
        if cached is not None and cached[0] is test_runner_fn:
            result = cached[1]
            return {**result, 'violations': result['violations'].copy()}
        violations = []
        patterns = {
            'Hardcoded secret': r'(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9_]{8,}|AKIA[A-Z0-9]{12,})',
            'Prompt injection delimiter': r'<\|im_start\|>|\[SYSTEM\]|\bsystem\s*:',
            'Unauthorized system call': r'\b(?:os\.system|os\.popen|subprocess\.(?:run|call|Popen|check_call|check_output)|os\.exec\w*|os\.spawn\w*)\s*\(',
        }
        for label, pattern in patterns.items():
            if re.search(pattern, candidate_code, re.IGNORECASE):
                violations.append(label)
        if self.domain == Domain.FINANCE:
            for label, pattern in [('Missing slippage check', r'\bslippage\b'), ('Missing fee check', r'\bfees?\b'), ('Missing drawdown limit', r'\b(?:max(?:imum)?_?drawdown|drawdown_?limit|drawdown)\b'), ('Missing CVaR check', r'\bcvar\b|\bcvar_\w+\b|\b\w+_cvar\b'), ('Missing drawdown velocity limit', r'\bdrawdown_?velocity\b|\bdrawdown_?velocity_\w+\b')]:
                if not re.search(pattern, candidate_code, re.IGNORECASE):
                    violations.append(label)
            if re.search(r'\bleverage\s*=\s*\d+(?:\.\d+)?', candidate_code, re.IGNORECASE) and not re.search(r'\b(?:max_leverage|leverage_limit|limit_leverage)\b', candidate_code, re.IGNORECASE):
                violations.append('Hardcoded unconstrained leverage')
        rate = 0.0
        if test_runner_fn is not None:
            try:
                result = test_runner_fn()
                if isinstance(result, dict):
                    rate = float(result['regression_rate'])
                elif isinstance(result, bool):
                    rate = 0.0 if result else 1.0
                else:
                    rate = float(result)
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError('invalid regression rate')
                if rate != 0.0:
                    violations.append('Regression detected')
            except Exception as exc:
                rate = 1.0
                violations.append(f'Regression check failed: {exc}')
        result = {'status': 'FAIL' if violations else 'PASS', 'regression_rate': rate, 'violations': violations}
        if not violations:
            self._cache[key] = (test_runner_fn, {**result, 'violations': violations.copy()})
        return result
