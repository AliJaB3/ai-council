class QuarantineManager:
    def __init__(self, store): self.store = store
    def propose(self, record): return self.store.propose(record)
    def validate(self, record_id, drift_verified=True): return self.store.revalidate(record_id, drift_verified)
    def revoke(self, record_id): return self.store.revoke(record_id)
