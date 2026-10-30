import hashlib
import json
from ...contracts.records import ExperimentResult, Verdict

class RegressionEvaluator:
    def __init__(self, runner, command): self.runner = runner; self.command = command
    def evaluate(self, changes, base_revision='unknown'):
        digest = hashlib.sha256(json.dumps(changes, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        baseline = self.runner.run(self.command)
        if baseline.get('status') != 'PASSED':
            return ExperimentResult(digest, base_revision, 'bubblewrap', {'baseline': baseline}, Verdict.HARD_FAIL)
        candidate = self.runner.run(self.command, changes)
        verdict = Verdict.PROMOTABLE if candidate.get('status') == 'PASSED' else Verdict.REJECTED
        return ExperimentResult(digest, base_revision, 'bubblewrap', {'baseline': baseline, 'candidate': candidate}, verdict)
