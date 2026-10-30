from abc import ABC, abstractmethod

class MemoryProvider(ABC):
    @abstractmethod
    def propose(self, record): ...
    @abstractmethod
    def retrieve(self, query, limit, tenant_id): ...
    @abstractmethod
    def revalidate(self, record_id, is_valid): ...
    @abstractmethod
    def revoke(self, record_id): ...
    @abstractmethod
    def snapshot(self): ...

class NullMemoryProvider(MemoryProvider):
    def propose(self, record): return record.id
    def retrieve(self, query, limit, tenant_id): return []
    def revalidate(self, record_id, is_valid): return None
    def revoke(self, record_id): return None
    def snapshot(self): return {'QUARANTINED': 0, 'VALIDATED': 0, 'REVOKED': 0, 'EXPIRED': 0}
