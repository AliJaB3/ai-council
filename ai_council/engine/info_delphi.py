"""Independent evidence views for the blind phase."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed

class InfoDelphi:
    def slice_evidence(self, grounding, seat_index=0, seat_count=1, asymmetric=False):
        if asymmetric and seat_count > 0:
            grounding = [g for i, g in enumerate(grounding) if i % seat_count == seat_index]
        return deepcopy(grounding)

    def evaluate(self, seats, topic, grounding, asymmetric=False):
        results, errors = {}, []
        with ThreadPoolExecutor(max_workers=max(1, len(seats))) as pool:
            futures = {pool.submit(seat.evaluate, topic, self.slice_evidence(grounding, i, len(seats), asymmetric)): (i, seat) for i, seat in enumerate(seats)}
            for future in as_completed(futures):
                i, seat = futures[future]
                try:
                    results[i] = future.result()
                except Exception as exc:
                    errors.append(f"{getattr(getattr(seat, 'config', None), 'role', i)}: {exc}")
        return [results[i] for i in sorted(results)], errors
