from ai_council.skills import (Domain, BlastRadius, ToolContract, SkillDefinition,
                               SkillRegistry, PreFlightHarness, builtin_registry)
from ai_council.cli import main


def test_models_and_registry():
    tool = ToolContract('inspect', Domain.RESEARCH, BlastRadius.READ_ONLY)
    assert tool.read_only and tool.timeout_s == 10
    skill = SkillDefinition('study', '1', Domain.RESEARCH, 'Research', BlastRadius.READ_ONLY, [tool], ['No fabrication'])
    registry = SkillRegistry()
    registry.register(skill)
    assert registry.get('study') is skill
    assert registry.get('missing') is None
    assert registry.resolve_jit(Domain.RESEARCH) == [skill]
    assert registry.list_skills(Domain.FINANCE) == []


def test_detection_and_builtins():
    registry = builtin_registry()
    for query, domain in [('trading orderbook funding', Domain.FINANCE), ('refactor code deadlock', Domain.ENGINEERING), ('prompt injection secret', Domain.SECURITY), ('system architecture', Domain.ARCHITECTURE), ('research literature', Domain.RESEARCH), ('hello', Domain.GENERAL)]:
        assert registry.detect_domain(query) == domain
    assert len(registry.list_skills()) == 3
    assert registry.resolve_jit(Domain.FINANCE)[0].name == 'QuantFinance'


def test_preflight():
    harness = PreFlightHarness()
    assert harness.verify_candidate('x = 1', lambda: 0)['status'] == 'PASS'
    assert harness.verify_candidate('token = "sk-abcdefgh1234"')['status'] == 'FAIL'
    assert harness.verify_candidate('"<|im_start|>"')['status'] == 'FAIL'
    assert harness.verify_candidate('os.system("id")')['status'] == 'FAIL'
    assert harness.verify_candidate('x = 1', lambda: 0.1)['status'] == 'FAIL'
    finance = PreFlightHarness(Domain.FINANCE)
    assert finance.verify_candidate('slippage = 0.01\nfee = 1\nmax_drawdown = 0.1')['status'] == 'PASS'
    assert finance.verify_candidate('leverage = 100')['status'] == 'FAIL'


def test_cli_list_skills(capsys):
    assert main(['--list-skills']) == 0
    output = capsys.readouterr().out
    assert 'QuantFinance' in output and 'READ_ONLY' in output
    assert main(['--list-skills', '--skill-domain', 'finance', '--json']) == 0
    assert 'finance' in capsys.readouterr().out


def test_orchestrator_loads_skill_in_system_instruction(tmp_path):
    from ai_council.config import Settings
    from ai_council.engine.orchestrator import CouncilOrchestrator
    from ai_council.seats import BaseSeat
    from ai_council.models import SeatOpinion, Claim, CouncilVerdict
    from ai_council.store.database import Database

    seen = []
    class Seat(BaseSeat):
        def evaluate(self, topic, grounding):
            seen.append(self.skill_instructions)
            return SeatOpinion('engineer', stance='SUPPORT', claims=[Claim('claim')])
        def cross_examine(self, topic, opinions):
            from ai_council.models import DialecticTurn
            return DialecticTurn('engineer')
    class Arbiter:
        def synthesize(self, topic, opinions, turns, graph, grounding):
            return CouncilVerdict(topic=topic, executive_verdict='done')
    settings = Settings()
    with Database(tmp_path / 'council.db') as store:
        result = CouncilOrchestrator(settings, seats=[Seat(settings.seats[0], settings)], arbiter=Arbiter(), store=store).deliberate('trading orderbook', skill_domain='engineering')
    assert 'Do not hold locks during I/O' in seen[0]
    assert result.audit_report['skill_domain'] == 'engineering'
    assert result.audit_report['active_skills'][0]['name'] == 'SystemsEngineering'
