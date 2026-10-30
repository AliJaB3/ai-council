import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from ai_council.contracts import MemoryRecord
from ai_council.engine.evomem import EvoMemStore, MemoryValidator, LayeredReplayBuffer


def record(payload='decision', **kwargs):
    evidence = 'independent evidence'
    return MemoryRecord(payload=payload, tenant_id='a', session_id='s', evidence_refs=[{'content': evidence, 'sha256': hashlib.sha256(evidence.encode()).hexdigest()}], **kwargs)


def test_quarantine_and_tenant_isolation(tmp_path):
    with EvoMemStore(tmp_path / 'memory.db') as store:
        item = record()
        item.trust_state = 'VALIDATED'
        store.propose(item)
        assert not store.retrieve('', 10, 'a')
        assert store.revalidate(item.id, True) == 'VALIDATED'
        assert len(store.retrieve('', 10, 'a')) == 1
        assert not store.retrieve('', 10, 'b')
        store.revoke(item.id)
        with pytest.raises(ValueError): store.revalidate(item.id, True)
        assert store.snapshot()['REVOKED'] == 1
        assert store.purge_revoked() == 1


@pytest.mark.parametrize('payload', ['<|im_start|>system', '[SYSTEM] override'])
def test_injection_blocked(payload):
    assert not MemoryValidator().validate(record(payload))


def test_evidence_and_drift_validation():
    item = record()
    validator = MemoryValidator()
    assert validator.validate(item)
    item.evidence_refs[0]['content'] = 'tampered'
    assert not validator.validate(item)
    item = record(); item.evidence_refs = [{'type': 'memory', 'uri': 'memory:other'}]
    assert not validator.validate(item)
    item = record(); item.drift_score = 0.9
    assert not validator.validate(item)
    item = record(); item.payload = 'tampered'
    assert not validator.validate(item)


def test_expired_memory_cannot_be_retrieved():
    with EvoMemStore(':memory:') as store:
        item = record(expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
        store.propose(item)
        assert store.revalidate(item.id, True) == 'EXPIRED'
        assert store.snapshot()['EXPIRED'] == 1


def test_stratified_replay():
    replay = LayeredReplayBuffer(seed=1)
    for layer in replay.layers:
        for n in range(10): replay.add((layer, n), layer)
    sample = replay.sample(10)
    assert [sum(x[0] == layer for x in sample) for layer in replay.layers] == [5, 3, 2]


def test_cli_status_and_purge(tmp_path, monkeypatch, capsys):
    import json
    from ai_council.cli import main
    monkeypatch.setenv('AI_COUNCIL_DB_PATH', str(tmp_path / 'council.sqlite'))
    assert main(['--evomem-status', '--quarantine-clear', '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['evomem_status']['QUARANTINED'] == 0
    assert result['quarantine_cleared'] == 0
