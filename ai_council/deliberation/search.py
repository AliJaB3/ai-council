"""A small, inspectable tree for deliberation search."""
import math
from uuid import uuid4
from ..contracts import SearchNode

class TreeOfDeliberation:
    def __init__(self, root=None):
        self.root = root or SearchNode(node_id=str(uuid4()))
        self.nodes = {self.root.node_id: self.root}
        self.children = {self.root.node_id: []}

    @staticmethod
    def compute_ucb(node, parent_visits, c=1.414, lam=2.0):
        return (node.value_sum / max(1, node.visits)
                + c * math.sqrt(math.log(max(1, parent_visits)) / max(1, node.visits))
                - lam * node.falsification_penalty)

    def expand(self, parent, actions):
        if self.nodes.get(parent.node_id) is not parent:
            raise ValueError('parent is not in this tree')
        result = []
        for action in actions:
            node = SearchNode(str(uuid4()), parent.node_id, action, dict(parent.state_snapshot),
                              falsification_penalty=parent.falsification_penalty)
            self.nodes[node.node_id] = node
            self.children[node.node_id] = []
            self.children[parent.node_id].append(node.node_id)
            result.append(node)
        return result

    def apply_falsification_penalty(self, node_id, penalty):
        if not math.isfinite(penalty) or penalty < 0:
            raise ValueError('penalty must be finite and nonnegative')
        # Penalize the whole descendant branch so selecting deeper nodes cannot evade it.
        pending = [node_id]
        while pending:
            current = pending.pop()
            self.nodes[current].falsification_penalty += penalty
            pending.extend(self.children[current])

    def best_path(self):
        path = [self.root]
        while self.children[path[-1].node_id]:
            parent = path[-1]
            path.append(max((self.nodes[n] for n in self.children[parent.node_id]),
                            key=lambda n: self.compute_ucb(n, parent.visits)))
        return path
