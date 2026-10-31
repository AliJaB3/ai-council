import math
import pytest
from ai_council.contracts import SearchNode, ObjectionRecord
from ai_council.deliberation.search import TreeOfDeliberation
from ai_council.evidence.gateway import EvidenceGateway
from ai_council.evidence.pump import EvidencePump
from ai_council.falsification.harness import CounterExampleHarness, FalsificationOutcome
from ai_council.governance.delegation import LiquidDelegation
from ai_council.governance.quadratic import QuadraticVoting
from ai_council.engine.mcp_client import MCPTool
from ai_council.engine.sandbox_runner import IsolatedSandboxRunner

def test_tree_ucb_and_penalty():
    tree = TreeOfDeliberation(SearchNode('root', visits=10))
    a, b = tree.expand(tree.root, ['a', 'b'])
    a.visits, a.value_sum = 2, 1
    assert tree.compute_ucb(a, 10) == pytest.approx(.5 + 1.414 * math.sqrt(math.log(10) / 2))
    tree.apply_falsification_penalty(a.node_id, 2)
    child = tree.expand(a, ['child'])[0]
    assert child.falsification_penalty == 2
    assert tree.best_path()[1] is b

def test_gateway_and_pump():
    class Client:
        def list_tools(self):
            return [MCPTool('search', '', {}, False), MCPTool('write', '', {}, True)]
        def call_tool(self, name, args):
            return args
    gateway = EvidenceGateway(Client())
    with pytest.raises(PermissionError): gateway.call_tool('write')
    envelope = EvidencePump().inject('hello', gateway, 'search', {})
    assert not envelope.is_trusted and 'hello' in envelope.content
    assert EvidencePump.should_pump(.8, 1)
    assert not EvidencePump.should_pump(.8, 0)

def test_falsification():
    harness, runner = CounterExampleHarness(), IsolatedSandboxRunner()
    def evaluate(code): return harness.evaluate_objection(ObjectionRecord('o', 'c', code), runner)[0]
    assert evaluate('assert 1 == 1') == FalsificationOutcome.REFUTED
    assert evaluate('assert 1 == 2') == FalsificationOutcome.NOT_REFUTED
    assert evaluate('raise ValueError("bad")') == FalsificationOutcome.EXECUTION_ERROR
    assert evaluate('') == FalsificationOutcome.INCONCLUSIVE

def test_governance():
    delegation = LiquidDelegation()
    delegation.delegate('a', 'b')
    delegation.delegate('b', 'c')
    with pytest.raises(ValueError): delegation.delegate('c', 'a')
    result = delegation.resolve_effective_votes({'a': 1, 'b': 1, 'c': 1, 'd': 1})
    assert result['c'] == pytest.approx(1.6)
    voting = QuadraticVoting()
    assert voting.cast_vote('a', 4, 2)[0]
    assert not voting.cast_vote('a', 3, 2)[0]
