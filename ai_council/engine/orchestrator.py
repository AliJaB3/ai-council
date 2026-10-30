"""Three-phase council orchestration."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from ..config import Settings
from ..seats import BaseSeat, ArbiterSeat, SeatError
from ..store.database import Database
from .claim_graph import ClaimGraph
from .grounding import read_files

class CouncilOrchestrator:
    def __init__(self, settings=None, seats=None, arbiter=None, store=None):
        self.settings = settings or Settings()
        self.seats = list(seats) if seats is not None else [BaseSeat(c, self.settings) for c in self.settings.seats]
        self.arbiter = arbiter or BaseArbiter(self.settings)
        self.store = store
    @staticmethod
    def _parallel(seats, method, *args):
        results, errors = {}, []
        if not seats: return [], []
        with ThreadPoolExecutor(max_workers=len(seats)) as pool:
            futures = {pool.submit(getattr(seat, method), *args): (i, seat) for i, seat in enumerate(seats)}
            for future in as_completed(futures):
                i, seat = futures[future]
                try: results[i] = future.result()
                except Exception as exc: errors.append(f"{getattr(getattr(seat, 'config', None), 'role', i)}: {exc}")
        return [results[i] for i in sorted(results)], errors
    def deliberate(self, topic, files=None, deep=False):
        if not topic or not topic.strip(): raise ValueError("topic is required")
        start = time.monotonic()
        grounding = read_files(files or [])
        missing = [item['path'] for item in grounding if not item['exists']]
        if missing: raise FileNotFoundError(", ".join(missing))
        opinions, errors = self._parallel(self.seats, 'evaluate', topic, grounding)
        if not opinions: raise SeatError("All seats failed: " + "; ".join(errors))
        turns, dialectic_errors = self._parallel(self.seats, 'cross_examine', topic, opinions) if deep else ([], [])
        errors += dialectic_errors
        graph = ClaimGraph(opinions).to_dict()
        verdict = self.arbiter.synthesize(topic, opinions, turns, graph, grounding)
        verdict.duration_s = time.monotonic() - start
        if errors: verdict.status = 'PARTIAL'
        own_store = self.store is None
        store = self.store or Database(self.settings.db_path)
        try: store.save(verdict, opinions, turns, graph, grounding)
        finally:
            if own_store: store.close()
        return verdict
    run = deliberate

class BaseArbiter(ArbiterSeat):
    def __init__(self, settings):
        BaseSeat.__init__(self, settings.arbiter, settings)
