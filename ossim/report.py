"""Text and image output for schedules and paging results."""

from __future__ import annotations

from .memory import PagingResult
from .scheduling import Process, Schedule


def gantt_text(s: Schedule, scale: int = 2) -> str:
    """ASCII Gantt chart, e.g.
    |  P1  |P2|    P3    |
    0      3  4          9
    """
    top, bottom = "|", "0"
    for sl in s.gantt:
        width = max(len(sl.pid) + 2, (sl.end - sl.start) * scale)
        label = "--" if sl.pid == "idle" else sl.pid
        top += label.center(width) + "|"
        bottom += " " * (width + 1 - len(str(sl.end))) + str(sl.end)
    return f"{top}\n{bottom}"


def metrics_table(s: Schedule, processes: list[Process]) -> str:
    m = s.metrics(processes)
    cols = ["arrival", "burst", "completion", "turnaround", "waiting", "response"]
    lines = ["PID   " + "".join(c[:10].rjust(11) for c in cols)]
    for pid, row in m.items():
        lines.append(f"{pid:<6}" + "".join(str(row[c]).rjust(11) for c in cols))
    avg = s.averages(processes)
    lines.append("")
    lines.append(
        f"avg waiting {avg['avg_waiting']}  |  avg turnaround {avg['avg_turnaround']}  |  "
        f"avg response {avg['avg_response']}  |  CPU {avg['cpu_utilization']}%  |  "
        f"context switches {s.context_switches}"
    )
    return "\n".join(lines)


def paging_table(refs: list[int], r: PagingResult) -> str:
    n = len(r.frames_history[0]) if r.frames_history else 0
    lines = ["ref    " + " ".join(f"{x:>3}" for x in refs)]
    for f in range(n):
        cells = [r.frames_history[t][f] for t in range(len(refs))]
        lines.append(f"frame{f} " + " ".join("  ." if c is None else f"{c:>3}" for c in cells))
    lines.append("fault  " + " ".join("  *" if x else "   " for x in r.faults))
    lines.append(f"{r.algorithm}: {r.fault_count} page faults, hit ratio {r.hit_ratio}")
    return "\n".join(lines)


def save_gantt_png(schedules: list[Schedule], path: str) -> None:
    """Draws one Gantt row per algorithm (requires matplotlib)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pids = sorted({sl.pid for s in schedules for sl in s.gantt if sl.pid != "idle"})
    cmap = plt.get_cmap("tab10")
    colors = {pid: cmap(i % 10) for i, pid in enumerate(pids)}
    colors["idle"] = "#dddddd"

    fig, ax = plt.subplots(figsize=(11, 0.8 * len(schedules) + 1.2))
    for row, s in enumerate(reversed(schedules)):
        for sl in s.gantt:
            ax.barh(row, sl.end - sl.start, left=sl.start, color=colors[sl.pid], edgecolor="black", height=0.6)
            if sl.pid != "idle" and sl.end - sl.start >= 1:
                ax.text((sl.start + sl.end) / 2, row, sl.pid, ha="center", va="center", fontsize=8)
    ax.set_yticks(range(len(schedules)), [s.algorithm for s in reversed(schedules)])
    ax.set_xlabel("time")
    ax.set_title("CPU scheduling comparison")
    ax.grid(axis="x", linestyle=":", alpha=0.6)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
