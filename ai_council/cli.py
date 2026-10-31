"""Command-line entry point."""
import argparse
import json
import sys
from .config import Settings
from .engine.orchestrator import CouncilOrchestrator
from .store.database import Database
from .engine.evomem import EvoMemStore
from pathlib import Path
import shlex
from .skills import builtin_registry
from .skills.models import Domain
from .workshop import AutonomousCrucibleWorkshop
from .workshop.models import Domain as WorkshopDomain, IdeaStatus
from dataclasses import asdict

def _render_record(record, seats=(), audit=False):
    verdict = record.get("verdict") or {}
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    print(f"\n⚖️  {verdict.get('topic', 'Council verdict')}")
    print(f"   {verdict.get('status', 'UNKNOWN')} · Confidence {number(verdict.get('confidence_score')):g}/10 · {number(verdict.get('duration_s')):.2f}s")
    print(f"   Decision: {verdict.get('id', '')} · Arbiter: {verdict.get('judge_model') or '—'}")
    report = verdict.get('audit_report') or {}
    if report:
        for skill in report.get('active_skills', []):
            print(f"   🎯 Active Domain Skill: {skill['name']} (v{skill['version']} · {skill['blast_radius']})")
        print(f"   🎯 DRIFT Evidence Score: {number(report.get('support_ratio')):.0%} [{report.get('status', 'UNKNOWN')}]")
        consensus = report.get('consensus') or {}
        print(f"   Armor Consensus: {'SYCOPHANCY RISK' if consensus.get('sycophancy_risk') else 'GROUNDED' if consensus.get('can_early_exit') else 'DELIBERATE'} · entropy {number(consensus.get('consensus_entropy')):.2f}")
        if audit:
            print(f"   Claims: {report.get('supported_claims', 0)}/{report.get('total_claims', 0)} supported")
            for detail in report.get('unsupported_details', []):
                print(f"   • {detail.get('role', '')}: {detail.get('text', '')} — {detail.get('reason', '')}")
    opinions = record.get("opinions") or []
    if opinions or seats:
        print("\n👥  Council seats")
        by_role = {opinion.get('role'): opinion for opinion in opinions if opinion.get('role')}
        for opinion in opinions:
            stance = opinion.get('stance', 'UNKNOWN')
            icon = {'SUPPORT': '✅', 'OPPOSE': '❌', 'AMEND': '🔧'}.get(stance, '•')
            print(f"  {opinion.get('avatar') or '👤'}  {opinion.get('title') or opinion.get('role') or 'Specialist'}  {icon} {stance} · {opinion.get('confidence', 0)}/10 · {number(opinion.get('latency_ms')):.0f} ms")
            if opinion.get('model_used'):
                print(f"      {opinion['model_used']}")
            if opinion.get('argument'):
                print(f"      {opinion['argument']}")
        for seat in seats:
            if seat.role not in by_role:
                print(f"  {seat.avatar}  {seat.title}  ⚠️ No opinion returned")
    turns = record.get('turns') or []
    if turns:
        print("\n💬  Dialectic turns")
        for turn in turns:
            print(f"  • {turn.get('seat_role') or turn.get('role') or turn.get('title') or 'Specialist'} · {turn.get('evolved_stance', 'UNKNOWN')}")
            for label, target, point in (('Challenge', turn.get('challenge_target'), turn.get('challenge_point')), ('Synergy', turn.get('synergy_target'), turn.get('synergy_point'))):
                if point:
                    print(f"    {label}{f' → {target}' if target else ''}: {point}")
            if turn.get('text'):
                print(f"    {turn['text']}")
    for key, title in (("executive_verdict", "Executive verdict"), ("emergent_architecture", "Emergent architecture"), ("consensus_analysis", "Consensus analysis"), ("implementation_blueprint", "Implementation blueprint"), ("risk_matrix", "Risk matrix"), ("kill_switch_criteria", "Kill switch criteria")):
        if verdict.get(key):
            print(f"\n## {title}\n\n{verdict[key]}")


def _render_output(output, store, settings, audit=False):
    if "skills" in output:
        print("Skill  Domain  Version  Blast radius")
        for skill in output["skills"]: print(f"{skill['name']}  {skill['domain']}  {skill['version']}  {skill['blast_radius']}")
    if "evomem_status" in output: print("EvoMem: " + ", ".join(f"{k.lower()}: {v}" for k, v in output["evomem_status"].items()))
    if "quarantine_cleared" in output: print(f"Revoked memories purged: {output['quarantine_cleared']}")
    if 'stale' in output:
        stale = output['stale']
        print(f"🔄  Stale decisions: {len(stale)}")
        for decision_id in stale:
            print(f"  • {decision_id}")
    for key, title in (('history', 'History'), ('search', 'Search results')):
        if key in output:
            print(f"\n📚  {title} · {len(output[key])} decision(s)")
            for record in output[key]:
                _render_record(record, audit=audit)
    if 'verdict' in output:
        verdict = output['verdict']
        _render_record(store.get(verdict['id']) or {'verdict': verdict}, settings.seats, audit=audit)

def main(argv=None):
    parser = argparse.ArgumentParser(prog="ai-council", description="Convene the AI Council")
    parser.add_argument("topic", nargs="?")
    parser.add_argument("--file", action="append", default=[], help="Ground deliberation in a file; repeatable")
    parser.add_argument("--skill-domain", choices=["auto", "engineering", "finance", "security", "architecture", "research"], default="auto")
    parser.add_argument("--list-skills", action="store_true", help="List registered skills")
    parser.add_argument("--preflight", action="store_true", help="Enforce candidate pre-flight checks")
    parser.add_argument("--deep", action="store_true", help="Run dialectical cross-examination")
    parser.add_argument("--early-exit", action="store_true", help="Allow grounded consensus to skip cross-examination")
    parser.add_argument("--audit", action="store_true", help="Show detailed evidence audit")
    parser.add_argument("--strict-audit", action="store_true", help="Reject evidence deficits")
    parser.add_argument("--seal", action="store_true", help="Enable isolated candidate validation")
    parser.add_argument("--seal-candidate", metavar="JSON", help="JSON file mapping workspace paths to replacement contents")
    parser.add_argument("--seal-command", help="Baseline test command (argument string, no shell)")
    parser.add_argument("--evomem", action="store_true", help="Enable continuous memory")
    parser.add_argument("--evomem-status", action="store_true", help="Show memory state counts")
    parser.add_argument("--quarantine-clear", action="store_true", help="Purge revoked memories")
    parser.add_argument("--tenant-id", default="default")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--search", metavar="TERM")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-stale", action="store_true")
    parser.add_argument("--workshop", action="store_true", help="Run an ideation workshop on the topic")
    parser.add_argument("--workshop-count", type=int, default=3, help="Number of workshop candidates to generate (default: 3)")
    parser.add_argument("--workshop-domain", type=str.upper, choices=[d.value for d in WorkshopDomain], help="Crucible target domain")
    parser.add_argument("--crucible-strict", action="store_true", help="Return failure if any candidate remains rejected")
    args = parser.parse_args(argv)
    if args.workshop and not args.topic: parser.error("--workshop requires a topic")
    if not (args.topic or args.history or args.search is not None or args.check_stale or args.evomem_status or args.quarantine_clear or args.list_skills): parser.error("provide a topic, --history, --search, or --check-stale")
    try:
        if args.workshop:
            workshop = AutonomousCrucibleWorkshop(count=args.workshop_count, strict=args.crucible_strict)
            survivors = workshop.run_cycle(args.topic, domain=WorkshopDomain(args.workshop_domain) if args.workshop_domain else None)
            if args.json:
                print(json.dumps({'ideas': [asdict(idea) for idea in workshop.candidates]}, ensure_ascii=False, indent=2))
            else:
                print(f"\n💡 Ideation workshop: {args.topic}")
                for idea in workshop.candidates:
                    print(f"\n{'✅' if idea.status.value == 'VALIDATED' else '❌'} [{idea.status.value}] {idea.title}")
                    print(f"  Problem: {idea.problem_statement}")
                    mechanism = idea.causal_mechanism
                    contract = idea.invariant_contract
                    print(f"  [AXIOMATIC: {'FAIL' if idea.status == IdeaStatus.TIER_0_REJECTED else 'PASS'}] [CONTRACT: {'NOT RUN' if idea.status == IdeaStatus.TIER_0_REJECTED else 'FAIL' if idea.status == IdeaStatus.TIER_1_REJECTED else 'PASS'}] [STATUS: {idea.status.value}]")
                    print(f"  Mechanism: trigger={mechanism.trigger_event}; node={mechanism.causal_node}; intervention={mechanism.intervention}; outcome={mechanism.predicted_outcome}; metric={mechanism.falsification_metric}; threshold={mechanism.falsification_threshold}")
                    print(f"  Contract: preconditions={contract.preconditions}; postconditions={contract.postconditions}; time={contract.complexity_time}; space={contract.complexity_space}; latency={contract.max_latency_budget_ns} ns; capital risk=${contract.max_capital_risk_usd:.2f}")
                    print(f"  Baseline: {idea.baseline_reference}")
                    print(f"  Cheapest falsification test: {idea.cheapest_falsification_test}")
                    if idea.falsification_reason: print(f"  Rejection reason: {idea.falsification_reason}")
            return 1 if args.crucible_strict and len(survivors) < args.workshop_count else 0
        if args.list_skills and not (args.topic or args.history or args.search is not None or args.check_stale or args.evomem_status or args.quarantine_clear):
            skills = builtin_registry().list_skills()
            if args.json:
                print(json.dumps([{'name': s.name, 'domain': s.domain.value, 'version': s.version, 'blast_radius': s.blast_radius.value} for s in skills], indent=2))
            else:
                print("Skill  Domain  Version  Blast radius")
                for s in skills: print(f"{s.name}  {s.domain.value}  {s.version}  {s.blast_radius.value}")
            return 0
        settings = Settings()
        if bool(args.seal_candidate) != bool(args.seal_command) or (args.seal_candidate and not args.seal): raise ValueError("--seal-candidate and --seal-command require --seal and each other")
        memory_path = str(Path(settings.db_path).with_suffix(".evomem.sqlite"))
        with EvoMemStore(memory_path) as memory, Database(settings.db_path) as store:
            output = {}
            if args.list_skills: output["skills"] = [{"name": s.name, "domain": s.domain.value, "version": s.version, "blast_radius": s.blast_radius.value} for s in builtin_registry().list_skills()]
            if args.check_stale: output['stale'] = store.check_stale()
            if args.history: output['history'] = store.history()
            if args.search is not None: output['search'] = store.search(args.search)
            if args.evomem_status: output['evomem_status'] = memory.snapshot()
            if args.quarantine_clear: output['quarantine_cleared'] = memory.purge_revoked()
            if args.topic:
                candidate = json.loads(Path(args.seal_candidate).read_text()) if args.seal_candidate else None
                output['verdict'] = CouncilOrchestrator(settings, store=store, enable_seal=args.seal, enable_evomem=args.evomem, memory_provider=memory, tenant_id=args.tenant_id).deliberate(args.topic, args.file, args.deep, early_exit=args.early_exit, strict_audit=args.strict_audit, code_candidate=candidate, seal_command=shlex.split(args.seal_command) if args.seal_command else None, skill_domain=args.skill_domain, preflight=args.preflight).to_dict()
            if args.json: print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                _render_output(output, store, settings, audit=args.audit)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ai-council: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
