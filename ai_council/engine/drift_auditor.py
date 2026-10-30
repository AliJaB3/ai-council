"""Heuristic evidence audit for claims made during deliberation."""
from dataclasses import dataclass, field
from pathlib import Path
import re
from ..models import Claim, SeatOpinion

@dataclass
class AuditResult:
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    support_ratio: float = 1.0
    status: str = 'VALID'
    unsupported_details: list[dict] = field(default_factory=list)
    kill_switch_triggered: bool = False

class DriftAuditor:
    def audit(self, claims, grounding):
        evidence = [g for g in grounding if g.get('exists', True)]
        content = '\n'.join(str(g.get('content', '')) for g in evidence)
        paths = [str(g.get('path', '')) for g in evidence]
        flattened = []
        for item in claims:
            if isinstance(item, SeatOpinion):
                flattened.extend((claim, item.role) for claim in item.claims)
            elif isinstance(item, Claim):
                flattened.append((item, ''))
        unsupported = []
        for claim, role in flattened:
            text = claim.text
            references = re.findall(r'(?<![\w/])(?:[\w.-]+/)*[\w-]+\.(?:py|js|ts|json|yaml|yml|md|sql)\b', text, re.I)
            identifiers = re.findall(r'\b([A-Za-z_]\w*)\s*\(', text)
            missing_files = [p for p in references if not any(path.endswith(p) or Path(path).name == p for path in paths)]
            missing_ids = [i for i in identifiers if not re.search(r'\b' + re.escape(i) + r'\b', content)]
            words = re.findall(r'[A-Za-z_]\w{2,}', text.lower())
            stop = {'the','and','that','this','with','from','file','function','code','does','uses','has','are','for','not','will','should','implementation','supports'}
            meaningful = [w for w in words if w not in stop]
            source_match = bool(claim.source and any(claim.source in p or p.endswith(claim.source) for p in paths))
            matches = any(re.search(r'\b' + re.escape(w) + r'\b', content, re.I) for w in meaningful)
            supported = not missing_files and not missing_ids and bool(evidence) and (matches or source_match or bool(references))
            if not supported:
                unsupported.append({'text': text, 'source': claim.source, 'role': role, 'reason': 'Missing references: ' + ', '.join(missing_files + missing_ids) if missing_files or missing_ids else 'No matching grounded evidence'})
        total = len(flattened)
        ratio = (total - len(unsupported)) / total if total else 1.0
        deficit = total > 0 and ratio < .75
        return AuditResult(total, total-len(unsupported), len(unsupported), ratio, 'DEFICIT' if deficit else 'VALID', unsupported, deficit)
