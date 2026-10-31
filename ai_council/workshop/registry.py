"""Extensible, per-domain morphological dimensions."""
from .models import Domain


class DimensionRegistry:
    def __init__(self):
        self.packs = {}
        packs = {
            Domain.BINANCE_ALGO: (['L2/L3 orderbook depth', 'maker-taker latency delta', 'queue position decay'], ['spread collapse', 'toxic order flow', 'api rate limit burst'], ['stochastic queue positioning', 'kernel bypass socket', 'cancel-replace pipelining']),
            Domain.SOLANA_INFRA: (['Proof of History', 'Tower BFT', 'Turbine'], ['tpu packet loss', 'block packing inefficiency'], ['jito bundle auction', 'raw quic client']),
            Domain.LOW_LATENCY_DISTRIBUTED: (['io_uring', 'LMAX Disruptor', 'cache line padding'], ['cascading GC pause', 'tail latency amplification'], ['lock-free SPSC ring', 'SQPOLL io_uring']),
            Domain.OFFENSIVE_SEC: (['taint analysis', 'canary tokens'], ['prompt injection', 'secret leak'], ['differential prompt sandboxing', 'formal grammar pruning']),
        }
        for domain, (primitives, problems, mechanisms) in packs.items():
            self.register(domain, primitives=primitives, problems=problems, mechanisms=mechanisms, invariants=['Use isolated replay with no capital at risk'])

    def register(self, domain, *, primitives=(), problems=(), mechanisms=(), invariants=()):
        domain = Domain(domain)
        pack = self.packs.setdefault(domain, {key: [] for key in ('primitives', 'problems', 'mechanisms', 'invariants')})
        for key, values in (('primitives', primitives), ('problems', problems), ('mechanisms', mechanisms), ('invariants', invariants)):
            if isinstance(values, str):
                values = [values]
            pack[key].extend(value for value in values if value not in pack[key])

    def get(self, domain):
        return self.packs.get(Domain(domain), {'primitives': [], 'problems': [], 'mechanisms': [], 'invariants': []})
