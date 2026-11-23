"""Banker's algorithm for deadlock avoidance."""

from __future__ import annotations


def is_safe(available: list[int], maximum: list[list[int]], allocation: list[list[int]]) -> tuple[bool, list[int]]:
    """Returns (safe?, safe sequence of process indexes)."""
    n, m = len(maximum), len(available)
    need = [[maximum[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]
    if any(x < 0 for row in need for x in row):
        raise ValueError("allocation exceeds maximum claim")
    work = available[:]
    finished = [False] * n
    sequence: list[int] = []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finished[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocation[i][j]  # process finishes and releases its resources
                finished[i] = True
                sequence.append(i)
                progress = True
    return all(finished), sequence


def request(available, maximum, allocation, pid: int, req: list[int]) -> bool:
    """Grant the request only if the resulting state is still safe. Mutates the state on success."""
    m = len(available)
    need = [maximum[pid][j] - allocation[pid][j] for j in range(m)]
    if any(req[j] > need[j] for j in range(m)):
        raise ValueError("process exceeded its maximum claim")
    if any(req[j] > available[j] for j in range(m)):
        return False  # must wait
    new_avail = [available[j] - req[j] for j in range(m)]
    new_alloc = [row[:] for row in allocation]
    new_alloc[pid] = [allocation[pid][j] + req[j] for j in range(m)]
    safe, _ = is_safe(new_avail, maximum, new_alloc)
    if safe:
        available[:] = new_avail
        allocation[pid] = new_alloc[pid]
    return safe
