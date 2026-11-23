"""Command line interface.

  python -m ossim cpu examples/processes.csv --algo all --quantum 3 --png gantt.png
  python -m ossim paging "7 0 1 2 0 3 0 4 2 3 0 3 2" --frames 3
  python -m ossim banker examples/banker.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

from . import deadlock, report
from .memory import PAGING
from .scheduling import ALGORITHMS, Process, round_robin


def load_processes(path: str) -> list[Process]:
    with open(path, newline="", encoding="utf-8") as f:
        return [
            Process(row["pid"], int(row["arrival"]), int(row["burst"]), int(row.get("priority") or 0))
            for row in csv.DictReader(f)
        ]


def cmd_cpu(args) -> None:
    procs = load_processes(args.file)
    names = list(ALGORITHMS) if args.algo == "all" else [args.algo]
    schedules = []
    for name in names:
        s = round_robin(procs, args.quantum) if name == "rr" else ALGORITHMS[name](procs)
        schedules.append(s)
        print(f"\n===== {s.algorithm} =====")
        print(report.gantt_text(s))
        print()
        print(report.metrics_table(s, procs))

    if len(schedules) > 1:
        print("\n===== Comparison =====")
        print(f"{'algorithm':<24}{'avg wait':>10}{'avg TAT':>10}{'avg resp':>10}{'switches':>10}")
        for s in sorted(schedules, key=lambda s: s.averages(procs)["avg_waiting"]):
            a = s.averages(procs)
            print(f"{s.algorithm:<24}{a['avg_waiting']:>10}{a['avg_turnaround']:>10}{a['avg_response']:>10}{s.context_switches:>10}")
    if args.png:
        report.save_gantt_png(schedules, args.png)
        print(f"\nGantt chart saved to {args.png}")


def cmd_paging(args) -> None:
    refs = [int(x) for x in args.refs.replace(",", " ").split()]
    names = list(PAGING) if args.algo == "all" else [args.algo]
    for name in names:
        print()
        print(report.paging_table(refs, PAGING[name](refs, args.frames)))


def cmd_banker(args) -> None:
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    safe, seq = deadlock.is_safe(data["available"], data["max"], data["allocation"])
    if safe:
        print("SAFE state. Safe sequence: " + " -> ".join(f"P{i}" for i in seq))
    else:
        print("UNSAFE state: a deadlock is possible.")
    for req in data.get("requests", []):
        ok = deadlock.request(data["available"], data["max"], data["allocation"], req["pid"], req["resources"])
        print(f"Request P{req['pid']} {req['resources']}: {'GRANTED' if ok else 'DENIED (would be unsafe / must wait)'}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="ossim", description="Operating systems algorithms simulator")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("cpu", help="CPU scheduling")
    c.add_argument("file", help="CSV with columns pid,arrival,burst[,priority]")
    c.add_argument("--algo", choices=[*ALGORITHMS, "all"], default="all")
    c.add_argument("--quantum", type=int, default=2)
    c.add_argument("--png", help="save a Gantt chart image (needs matplotlib)")
    c.set_defaults(func=cmd_cpu)

    g = sub.add_parser("paging", help="page replacement")
    g.add_argument("refs", help='reference string, e.g. "7 0 1 2 0 3"')
    g.add_argument("--frames", type=int, default=3)
    g.add_argument("--algo", choices=[*PAGING, "all"], default="all")
    g.set_defaults(func=cmd_paging)

    b = sub.add_parser("banker", help="Banker's algorithm")
    b.add_argument("file", help="JSON with available, max, allocation, optional requests")
    b.set_defaults(func=cmd_banker)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except (ValueError, KeyError, FileNotFoundError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
