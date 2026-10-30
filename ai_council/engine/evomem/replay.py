"""Stratified replay with deterministic largest-remainder allocation."""
import random

class LayeredReplayBuffer:
    def __init__(self, seed=None):
        self.layers = {'recent': [], 'verified': [], 'failures': []}
        self.random = random.Random(seed)
    def add(self, item, layer='recent'):
        if layer not in self.layers: raise ValueError('unknown replay layer')
        self.layers[layer].append(item)
    def sample(self, count):
        if count < 0: raise ValueError('count must be nonnegative')
        keys = list(self.layers); weights = (0.5, 0.3, 0.2)
        raw = [count * w for w in weights]; sizes = [int(v) for v in raw]
        for i in sorted(range(3), key=lambda i: (raw[i]-sizes[i], -i), reverse=True)[:count-sum(sizes)]: sizes[i] += 1
        result = []
        for key, n in zip(keys, sizes): result.extend(self.random.sample(self.layers[key], min(n, len(self.layers[key]))))
        return result
