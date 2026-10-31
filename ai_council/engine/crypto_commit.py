"""Canonical commitments for the independent opinion phase."""
import hashlib
import hmac
import json


class CommitRevealManager:
    def generate_commitment(self, payload: dict, nonce: str) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        return hashlib.sha256((canonical + nonce).encode('utf-8')).hexdigest()

    def verify_reveal(self, commitment: str, payload: dict, nonce: str) -> bool:
        return hmac.compare_digest(commitment, self.generate_commitment(payload, nonce))
