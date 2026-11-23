"""CPU scheduling algorithms.

Every algorithm takes a list of Process and returns a Schedule: the Gantt chart
(list of slices) plus per-process metrics. Idle CPU time is shown as pid "idle".
"""

from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0  # smaller number = higher priority

    def __post_init__(self):
        if self.burst <= 0:
            raise ValueError(f"{self.pid}: burst time must be positive")
        if self.arrival < 0:
            raise ValueError(f"{self.pid}: arrival time cannot be negative")


@dataclass
class Slice:
    pid: str
    start: int
    end: int


@dataclass
class Schedule:
    algorithm: str
    gantt: list[Slice] = field(default_factory=list)
    completion: dict[str, int] = field(default_factory=dict)
    first_run: dict[str, int] = field(default_factory=dict)
    context_switches: int = 0

    def run(self, pid: str, start: int, end: int) -> None:
        if end <= start:
            return
        if self.gantt and self.gantt[-1].pid == pid and self.gantt[-1].end == start:
            self.gantt[-1].end = end  # merge adjacent slices of the same process
        else:
            if self.gantt and self.gantt[-1].pid != "idle" and pid != "idle":
                self.context_switches += 1
            self.gantt.append(Slice(pid, start, end))
        if pid != "idle":
            self.first_run.setdefault(pid, start)

    def metrics(self, processes: list[Process]) -> dict[str, dict[str, int]]:
        out = {}
        for p in processes:
            turnaround = self.completion[p.pid] - p.arrival
            out[p.pid] = {
                "arrival": p.arrival,
                "burst": p.burst,
                "completion": self.completion[p.pid],
                "turnaround": turnaround,
                "waiting": turnaround - p.burst,
                "response": self.first_run[p.pid] - p.arrival,
            }
        return out

    def averages(self, processes: list[Process]) -> dict[str, float]:
        m = self.metrics(processes)
        n = len(m)
        total_time = self.gantt[-1].end - self.gantt[0].start
        busy = sum(s.end - s.start for s in self.gantt if s.pid != "idle")
        return {
            "avg_waiting": round(sum(v["waiting"] for v in m.values()) / n, 2),
            "avg_turnaround": round(sum(v["turnaround"] for v in m.values()) / n, 2),
            "avg_response": round(sum(v["response"] for v in m.values()) / n, 2),
            "cpu_utilization": round(100 * busy / total_time, 1),
            "throughput": round(n / total_time, 3),
        }


def _check(processes: list[Process]) -> list[Process]:
    if not processes:
        raise ValueError("no processes given")
    pids = [p.pid for p in processes]
    if len(set(pids)) != len(pids):
        raise ValueError("process ids must be unique")
    return sorted(processes, key=lambda p: (p.arrival, p.pid))


# ---------------------------------------------------------------- non-preemptive
def _non_preemptive(processes: list[Process], name: str, key) -> Schedule:
    pending = _check(processes)
    s = Schedule(name)
    time, ready, i = 0, [], 0
    while i < len(pending) or ready:
        while i < len(pending) and pending[i].arrival <= time:
            heapq.heappush(ready, (key(pending[i]), pending[i].arrival, pending[i].pid, pending[i]))
            i += 1
        if not ready:
            s.run("idle", time, pending[i].arrival)
            time = pending[i].arrival
            continue
        *_, p = heapq.heappop(ready)
        s.run(p.pid, time, time + p.burst)
        time += p.burst
        s.completion[p.pid] = time
    return s


def fcfs(processes: list[Process]) -> Schedule:
    """First Come, First Served."""
    return _non_preemptive(processes, "FCFS", key=lambda p: p.arrival)


def sjf(processes: list[Process]) -> Schedule:
    """Shortest Job First (non-preemptive)."""
    return _non_preemptive(processes, "SJF", key=lambda p: p.burst)


def priority(processes: list[Process]) -> Schedule:
    """Priority scheduling (non-preemptive, lower number = higher priority)."""
    return _non_preemptive(processes, "Priority", key=lambda p: p.priority)


# ---------------------------------------------------------------- preemptive
def _preemptive(processes: list[Process], name: str, key) -> Schedule:
    """Re-evaluates the choice at every arrival: the best `key` always runs."""
    pending = _check(processes)
    s = Schedule(name)
    remaining = {p.pid: p.burst for p in pending}
    time, ready, i = 0, [], 0
    while i < len(pending) or ready:
        while i < len(pending) and pending[i].arrival <= time:
            p = pending[i]
            heapq.heappush(ready, (key(p, remaining[p.pid]), p.arrival, p.pid, p))
            i += 1
        if not ready:
            s.run("idle", time, pending[i].arrival)
            time = pending[i].arrival
            continue
        *_, p = heapq.heappop(ready)
        next_arrival = pending[i].arrival if i < len(pending) else float("inf")
        run_for = min(remaining[p.pid], next_arrival - time)
        s.run(p.pid, time, time + run_for)
        time += run_for
        remaining[p.pid] -= run_for
        if remaining[p.pid] == 0:
            s.completion[p.pid] = time
        else:
            heapq.heappush(ready, (key(p, remaining[p.pid]), p.arrival, p.pid, p))
    return s


def srtf(processes: list[Process]) -> Schedule:
    """Shortest Remaining Time First (preemptive SJF)."""
    return _preemptive(processes, "SRTF", key=lambda p, rem: rem)


def preemptive_priority(processes: list[Process]) -> Schedule:
    return _preemptive(processes, "Priority (preemptive)", key=lambda p, rem: p.priority)


def round_robin(processes: list[Process], quantum: int = 2) -> Schedule:
    """Round Robin. A process that arrives during a time slice enters the queue
    before the process whose slice just ended (the usual textbook convention)."""
    if quantum <= 0:
        raise ValueError("quantum must be positive")
    pending = _check(processes)
    s = Schedule(f"Round Robin (q={quantum})")
    remaining = {p.pid: p.burst for p in pending}
    queue: deque[Process] = deque()
    time, i = 0, 0

    def admit(until: int) -> None:
        nonlocal i
        while i < len(pending) and pending[i].arrival <= until:
            queue.append(pending[i])
            i += 1

    admit(time)
    while queue or i < len(pending):
        if not queue:
            s.run("idle", time, pending[i].arrival)
            time = pending[i].arrival
            admit(time)
            continue
        p = queue.popleft()
        run_for = min(quantum, remaining[p.pid])
        s.run(p.pid, time, time + run_for)
        time += run_for
        remaining[p.pid] -= run_for
        admit(time)
        if remaining[p.pid] == 0:
            s.completion[p.pid] = time
        else:
            queue.append(p)
    return s


ALGORITHMS = {
    "fcfs": fcfs,
    "sjf": sjf,
    "srtf": srtf,
    "priority": priority,
    "ppriority": preemptive_priority,
    "rr": round_robin,
}
