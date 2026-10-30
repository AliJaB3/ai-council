"""Command-line entry point."""
import argparse
import json
import sys
from .config import Settings
from .engine.orchestrator import CouncilOrchestrator
from .store.database import Database

def _render_record(record, seats=()):
    verdict = record["verdict"]
    print(f"\n⚖️  {verdict.get('topic', 'Council verdict')}")
    print(f"   {verdict.get('status', 'UNKNOWN')} · Confidence {verdict.get('confidence_score', 0):g}/10 · {verdict.get('duration_s', 0):.2f}s")
    print(f"   Decision: {verdict.get('id', '')} · Arbiter: {verdict.get('judge_model') or '—'}")
    opinions = record.get("opinions", [])
    if opinions or seats:
        print("\n👥  Council seats")
        by_role = {opinion['role']: opinion for opinion in opinions}
        for opinion in opinions:
            stance = opinion.get('stance', 'UNKNOWN')
            icon = {'SUPPORT': '✅', 'OPPOSE': '❌', 'AMEND': '🔧'}.get(stance, '•')
            print(f"  {opinion.get('avatar') or '👤'}  {opinion.get('title') or opinion['role']}  {icon} {stance} · {opinion.get('confidence', 0)}/10 · {opinion.get('latency_ms', 0):.0f} ms")
            if opinion.get('model_used'):
                print(f"      {opinion['model_used']}")
            if opinion.get('argument'):
                print(f"      {opinion['argument']}")
        for seat in seats:
            if seat.role not in by_role:
                print(f"  {seat.avatar}  {seat.title}  ⚠️ No opinion returned")
    turns = record.get('turns', [])
    if turns:
        print("\n💬  Dialectic turns")
        for turn in turns:
            print(f"  • {turn['seat_role']} · {turn.get('evolved_stance', 'UNKNOWN')}")
            for label, target, point in (('Challenge', turn.get('challenge_target'), turn.get('challenge_point')), ('Synergy', turn.get('synergy_target'), turn.get('synergy_point'))):
                if point:
                    print(f"    {label}{' → ' + target if target else ''}: {point}")
            if turn.get('text'):
                print(f"    {turn['text']}")
    for key, title in (("executive_verdict", "Executive verdict"), ("emergent_architecture", "Emergent architecture"), ("consensus_analysis", "Consensus analysis"), ("implementation_blueprint", "Implementation blueprint"), ("risk_matrix", "Risk matrix"), ("kill_switch_criteria", "Kill switch criteria")):
        if verdict.get(key):
            print(f"\n## {title}\n\n{verdict[key]}")


def _render_output(output, store, settings):
    if 'stale' in output:
        stale = output['stale']
        print(f"🔄  Stale decisions: {len(stale)}")
        for decision_id in stale:
            print(f"  • {decision_id}")
    for key, title in (('history', 'History'), ('search', 'Search results')):
        if key in output:
            print(f"\n📚  {title} · {len(output[key])} decision(s)")
            for record in output[key]:
                _render_record(record)
    if 'verdict' in output:
        verdict = output['verdict']
        _render_record(store.get(verdict['id']) or {'verdict': verdict}, settings.seats)

def main(argv=None):
    parser = argparse.ArgumentParser(prog="ai-council", description="Convene the AI Council")
    parser.add_argument("topic", nargs="?")
    parser.add_argument("--file", action="append", default=[], help="Ground deliberation in a file; repeatable")
    parser.add_argument("--deep", action="store_true", help="Run dialectical cross-examination")
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
            if args.topic: output['verdict'] = CouncilOrchestrator(settings, store=store).deliberate(args.topic, args.file, args.deep).to_dict()
            if args.json: print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                _render_output(output, store, settings)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ai-council: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
