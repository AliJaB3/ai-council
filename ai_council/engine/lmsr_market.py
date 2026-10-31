"""Numerically stable, in-memory LMSR shadow markets."""
import math


class LMSRShadowMarket:
    def __init__(self):
        self.markets = {}

    def open_market(self, claim_id, correlation_id, b=100.0):
        if not math.isfinite(b) or b <= 0:
            raise ValueError('liquidity must be positive and finite')
        if claim_id in self.markets:
            raise ValueError('market already exists')
        self.markets[claim_id] = dict(claim_id=claim_id, correlation_id=correlation_id, b=float(b), q_yes=0.0, q_no=0.0, bets=[], settled=False)
        return self.get_market_state(claim_id)

    def get_market_state(self, claim_id):
        m = self.markets[claim_id]
        x, y = m['q_yes'] / m['b'], m['q_no'] / m['b']
        high = max(x, y)
        ex, ey = math.exp(x-high), math.exp(y-high)
        return {k: m[k] for k in ('claim_id', 'correlation_id', 'b', 'q_yes', 'q_no', 'settled')} | {'probability_yes': ex/(ex+ey), 'probability_no': ey/(ex+ey), 'cost': m['b'] * (high + math.log(ex+ey))}

    def place_bet(self, claim_id, seat, stance, confidence):
        m = self.markets[claim_id]
        if m['settled']:
            raise ValueError('market already settled')
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 10:
            raise ValueError('confidence must be between 0 and 10')
        stance = stance.upper()
        if stance not in ('YES', 'NO', 'SUPPORT', 'OPPOSE'):
            raise ValueError('stance must be YES or NO')
        yes = stance in ('YES', 'SUPPORT')
        before = self.get_market_state(claim_id)
        m['q_yes' if yes else 'q_no'] += confidence
        after = self.get_market_state(claim_id)
        m['bets'].append(dict(seat=seat, yes=yes, shares=confidence, cost=after['cost']-before['cost'], forecast=confidence/10 if yes else 1-confidence/10))
        return after

    def settle(self, claim_id, outcome_yes):
        m = self.markets[claim_id]
        if m['settled']:
            raise ValueError('market already settled')
        m['settled'] = True
        payoffs = {}
        for bet in m['bets']:
            payoffs[bet['seat']] = payoffs.get(bet['seat'], 0.0) + (bet['shares'] if bet['yes'] == outcome_yes else 0) - bet['cost']
        scores = [(bet['forecast'] - float(outcome_yes))**2 for bet in m['bets']]
        return {'claim_id': claim_id, 'outcome_yes': outcome_yes, 'payoffs': payoffs, 'brier_score': sum(scores)/len(scores) if scores else None, 'market_state': self.get_market_state(claim_id)}
