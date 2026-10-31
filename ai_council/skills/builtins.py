"""Standard domain skills."""
from .models import BlastRadius, Domain, SkillDefinition
from .registry import SkillRegistry

SystemsEngineeringSkill = SkillDefinition('SystemsEngineering', '1.0.0', Domain.ENGINEERING, 'Safe systems engineering.', BlastRadius.ISOLATED_SANDBOX, negative_constraints=['Do not hold locks during I/O.'])
QuantFinanceSkill = SkillDefinition('QuantFinance', '1.0.0', Domain.FINANCE, 'Risk-aware quantitative finance.', BlastRadius.READ_ONLY, negative_constraints=['Do not curve fit without walk-forward validation.', 'Do not omit slippage or fees.'])
AdversarialSecuritySkill = SkillDefinition('AdversarialSecurity', '1.0.0', Domain.SECURITY, 'Adversarial security analysis.', BlastRadius.ISOLATED_SANDBOX, negative_constraints=['Do not concatenate raw prompts.', 'Do not expose secrets.'])
ProbabilisticRiskSkill = SkillDefinition('ProbabilisticRisk', '1.0.0', Domain.FINANCE, 'Probabilistic financial risk analysis.', BlastRadius.READ_ONLY, negative_constraints=['Do not execute trades without 99% CVaR check.', 'Do not ignore drawdown velocity limits.'])
DialecticConsensusSkill = SkillDefinition('DialecticConsensus', '1.0.0', Domain.ARCHITECTURE, 'Evidence-grounded architectural consensus.', BlastRadius.READ_ONLY, negative_constraints=['Do not approve consensus without cross-peer challenge.', 'Do not accept unsubstantiated assertions without evidence grounding.'])


def builtin_registry():
    return SkillRegistry([SystemsEngineeringSkill, QuantFinanceSkill, AdversarialSecuritySkill, ProbabilisticRiskSkill, DialecticConsensusSkill])
