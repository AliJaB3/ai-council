class QuarantineManager:
    def __init__(self, store): self.store = store
    def propose(self, record): return self.store.propose(record)
    def validate(self, record_id, drift_verified=True): return self.store.revalidate(record_id, drift_verified)
    def revoke(self, record_id): return self.store.revoke(record_id)
    def promote(self, record_id: str, regression_passed: bool = True) -> bool:
        from ...contracts.records import TrustState
        with self.store.lock:
            record = self.store._get(record_id)
            if record.trust_state != TrustState.QUARANTINED:
                return False
            if not regression_passed:
                self.store.revoke(record_id)
                return False
            return self.store.revalidate(record_id, True) == TrustState.VALIDATED
