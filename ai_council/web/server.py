"""ASGI dashboard and background deliberation service."""
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..config import Settings
from ..engine.brier_calibration import BrierEngine
from ..engine.evomem import EvoMemStore, QuarantineManager
from ..engine.orchestrator import CouncilOrchestrator
from ..engine.streaming import DeliberationEventStream
from ..store.database import Database
from ..workshop import AutonomousCrucibleWorkshop
from .contracts import RunSnapshot, SeatTelemetry, StreamEvent


class ConveneRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=10000)
    deep: bool = False
    fast_path: bool = False

class WorkshopRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=10000)
    count: int = Field(default=3, ge=1, le=20)


def create_app(settings=None):
    settings = settings or Settings()
    app = FastAPI(title="AI Council Dashboard")
    app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Last-Event-ID"])
    lock = threading.RLock()
    runs = {}
    ideas = []
    app.state.runs = runs
    app.state.settings = settings

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def snapshot(record, run_id=None):
        v = record['verdict']
        return asdict(RunSnapshot(run_id or v['id'], v.get('topic', ''), v.get('status', ''), v.get('confidence_score', 0), v.get('duration_s', 0), v.get('created_at', ''), v, record.get('opinions', []), record.get('graph', {}), v.get('seat_weights') or {}, v.get('experiment_spec')))

    def publish(run_id, event_type, payload):
        with lock:
            run = runs[run_id]
            event = StreamEvent(str(uuid4()), run_id, len(run['events']) + 1, time.time(), event_type, payload)
            run['events'].append(asdict(event))

    def worker(run_id, body):
        with lock:
            runs[run_id]['status'] = 'RUNNING'
        publish(run_id, 'RUN_STARTED', {})
        stream = DeliberationEventStream()
        stream.subscribe(lambda event: publish(run_id, event.event_type, event.payload))
        try:
            with Database(settings.db_path) as store:
                verdict = CouncilOrchestrator(settings, store=store, event_stream=stream).deliberate(body.topic, deep=body.deep, fast_path=body.fast_path)
                record = store.get(verdict.id)
            with lock:
                runs[run_id]['record'] = record
                runs[run_id]['status'] = verdict.status
                publish(run_id, 'RUN_COMPLETED', {'verdict_id': verdict.id, 'status': verdict.status})
        except Exception as exc:
            with lock:
                runs[run_id]['status'] = 'FAILED'
                runs[run_id]['error'] = str(exc)
                publish(run_id, 'RUN_FAILED', {'error': str(exc)})

    @app.get('/')
    def index():
        return FileResponse(Path(__file__).parent / 'static' / 'dashboard.html', media_type='text/html')

    @app.get('/api/v1/runs')
    def list_runs():
        with Database(settings.db_path) as store:
            records = store.history()
        with lock:
            pending = [dict(run_id=k, topic=v['topic'], status=v['status'], created_at=v['created_at']) for k, v in runs.items() if not v.get('record')]
        return pending + [snapshot(record) for record in records]

    @app.get('/api/v1/runs/{run_id}/snapshot')
    def get_snapshot(run_id: str):
        with lock:
            run = runs.get(run_id)
            if run:
                if run.get('record'):
                    return snapshot(run['record'], run_id)
                return asdict(RunSnapshot(run_id, run['topic'], run['status'], 0, 0, run['created_at'], {'error': run.get('error')} if run.get('error') else {}, [], {}, {}, None))
        with Database(settings.db_path) as store:
            record = store.get(run_id)
        if not record:
            raise HTTPException(404, 'Run not found')
        return snapshot(record)

    @app.get('/api/v1/runs/{run_id}/stream')
    async def stream_run(run_id: str, request: Request):
        with lock:
            if run_id not in runs:
                raise HTTPException(404, 'Live run not found')
        last = request.headers.get('last-event-id', '0')
        try:
            cursor = max(0, int(last))
        except ValueError:
            cursor = 0
        async def events():
            nonlocal cursor
            while True:
                if await request.is_disconnected():
                    return
                with lock:
                    run = runs[run_id]
                    batch = [e for e in run['events'] if e['seq'] > cursor]
                    done = bool(run.get('record')) or run['status'] == 'FAILED'
                for event in batch:
                    cursor = event['seq']
                    yield f"id: {cursor}\nevent: {event['event_type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                if done:
                    return
                yield ': keepalive\n\n'
                await asyncio.sleep(1)
        return StreamingResponse(events(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.post('/api/v1/convene')
    def convene(body: ConveneRequest):
        if not body.topic.strip():
            raise HTTPException(422, 'Topic must not be blank')
        run_id = str(uuid4())
        with lock:
            runs[run_id] = {'topic': body.topic, 'status': 'PENDING', 'created_at': datetime.now(timezone.utc).isoformat(), 'events': []}
        threading.Thread(target=worker, args=(run_id, body), daemon=True, name='council-' + run_id[:8]).start()
        return {'run_id': run_id, 'status': 'PENDING'}

    @app.get('/api/v1/search')
    def search(q: str = ''):
        with Database(settings.db_path) as store:
            return [snapshot(record) for record in store.search(q)]

    @app.get('/api/v1/seats/status')
    def seats_status():
        brier = BrierEngine(settings.db_path)
        try:
            scores = {row['seat']: row for row in brier.status()}
        finally:
            brier.close()
        with Database(settings.db_path) as store:
            recent = store.history(limit=1)
        opinions = {o.get('role'): o for o in (recent[0]['opinions'] if recent else [])}
        result = []
        for seat in (*settings.seats, settings.arbiter):
            score, opinion = scores.get(seat.role, {}), opinions.get(seat.role, {})
            item = asdict(SeatTelemetry(seat.role, seat.title, seat.avatar, opinion.get('model_used') or seat.model, opinion.get('latency_ms', 0), score.get('score'), score.get('weight', 1.0), 'IDLE'))
            item.update(circuit_breaker='UNKNOWN', resolved=score.get('resolved', 0), checkpoints=[seat.model, *seat.fallbacks])
            result.append(item)
        return result

    @app.get('/api/v1/workshop/ideas')
    def workshop_ideas():
        with lock:
            return list(ideas)

    @app.post('/api/v1/workshop/run')
    def workshop_run(body: WorkshopRequest):
        if not body.topic.strip():
            raise HTTPException(422, 'Topic must not be blank')
        workshop = AutonomousCrucibleWorkshop(count=body.count)
        workshop.run_cycle(body.topic)
        result = [asdict(idea) for idea in workshop.candidates]
        with lock:
            ideas[:0] = result
            del ideas[100:]
        return result

    def memory_store():
        return EvoMemStore(str(Path(settings.db_path).with_suffix('.evomem.sqlite')))

    @app.get('/api/v1/evomem/status')
    def memory_status():
        with memory_store() as memory:
            counts = memory.snapshot()
            with memory.lock:
                rows = memory.db.execute("SELECT data FROM memories WHERE state='QUARANTINED' ORDER BY rowid DESC LIMIT 100").fetchall()
            return {'counts': counts, 'quarantined': [json.loads(row[0]) for row in rows]}

    @app.post('/api/v1/evomem/{record_id}/promote')
    def promote_memory(record_id: str):
        with memory_store() as memory:
            try:
                promoted = QuarantineManager(memory).promote(record_id)
            except KeyError:
                raise HTTPException(404, 'Memory not found')
        if not promoted:
            raise HTTPException(400, 'Memory failed validation or is not quarantined')
        return {'promoted': record_id}

    return app

app = create_app()
