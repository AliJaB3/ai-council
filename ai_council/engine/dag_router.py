"""Choose the next deliberation branch from the consensus assessment."""
class DAGRouter:
    def route(self, consensus, early_exit=False, deep=False):
        exit_now = bool(early_exit and consensus.get('can_early_exit'))
        challenge = bool(consensus.get('conflict') or consensus.get('adversarial_injection_needed'))
        return {'early_exit': exit_now, 'adversarial_challenge': challenge and not exit_now,
                'run_phase2': not exit_now and (deep or challenge)}
