"""Command-line entry point."""
import argparse
import json
import sys
from .config import Settings
from .engine.orchestrator import CouncilOrchestrator
from .store.database import Database

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
    parser.add_argument("--deep", action="store_true", help="Run dialectical cross-examination")
    parser.add_argument("--early-exit", action="store_true", help="Allow grounded consensus to skip cross-examination")
    parser.add_argument("--audit", action="store_true", help="Show detailed evidence audit")
    parser.add_argument("--strict-audit", action="store_true", help="Reject evidence deficits")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--search", metavar="TERM")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-stale", action="store_true")
    args = parser.parse_args(argv)
    if not (args.topic or args.history or args.search is not None or args.check_stale): parser.error("provide a topic, --history, --search, or --check-stale")
    try:
        settings = Settings()
        with Database(settings.db_path) as store:
            output = {}
            if args.check_stale: output['stale'] = store.check_stale()
            if args.history: output['history'] = store.history()
            if args.search is not None: output['search'] = store.search(args.search)
            if args.topic: output['verdict'] = CouncilOrchestrator(settings, store=store).deliberate(args.topic, args.file, args.deep, early_exit=args.early_exit, strict_audit=args.strict_audit).to_dict()
            if args.json: print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                _render_output(output, store, settings, audit=args.audit)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ai-council: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
