"""Quadratic voting budget validation."""
import math

class QuadraticVoting:
    def cast_vote(self, voter_id, budget, votes):
        if not math.isfinite(budget) or not math.isfinite(votes) or budget < 0:
            return False, 'Budget and votes must be finite; budget must be nonnegative', 0.0
        cost = votes * votes
        if cost > budget:
            return False, 'Insufficient budget', cost
        return True, 'Vote accepted', cost
