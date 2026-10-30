"""Fail-closed validation of untrusted memory and externally supplied evidence."""
import hashlib
import json
import re
import math
from ...contracts.records import content_digest

class MemoryValidator:
    def __init__(self, max_drift=0.25):
        self.max_drift = max_drift
    def validate(self, record):
        try:
            text = json.dumps({'payload': record.payload, 'provenance': record.provenance, 'evidence_refs': record.evidence_refs}, ensure_ascii=False)
            if re.search(r'<\|im_start\|>|\[\s*system\s*\]', text, re.I): return False
            if content_digest(record.payload) != record.content_hash: return False
            if not math.isfinite(float(record.drift_score)) or not 0 <= float(record.drift_score) <= self.max_drift: return False
            # References must include verifiable external content; a claimed digest alone is not evidence.
            external = False
            for ref in record.evidence_refs:
                if not isinstance(ref, dict): return False
                if ref.get('type') == 'memory' or str(ref.get('uri', '')).startswith('memory:'):
                    continue
                content, digest = ref.get('content'), ref.get('sha256')
                if not isinstance(content, str) or not isinstance(digest, str): return False
                if hashlib.sha256(content.encode()).hexdigest() != digest: return False
                external = True
            return external
        except (TypeError, ValueError, OverflowError):
            return False
