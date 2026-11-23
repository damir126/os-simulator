"""Page replacement algorithms (virtual memory)."""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass


@dataclass
class PagingResult:
    algorithm: str
    frames_history: list[list[int | None]]  # frame contents after each reference
    faults: list[bool]                       # was each reference a page fault?

    @property
    def fault_count(self) -> int:
        return sum(self.faults)

    @property
    def hit_ratio(self) -> float:
        return round(1 - self.fault_count / len(self.faults), 3) if self.faults else 0.0


def _snapshot(frames: list[int], n: int) -> list[int | None]:
    return frames + [None] * (n - len(frames))


def fifo(refs: list[int], n_frames: int) -> PagingResult:
    frames: list[int] = []
    order: deque[int] = deque()
    hist, faults = [], []
    for page in refs:
        fault = page not in frames
        if fault:
            if len(frames) < n_frames:
                frames.append(page)
            else:
                victim = order.popleft()
                frames[frames.index(victim)] = page
            order.append(page)
        faults.append(fault)
        hist.append(_snapshot(frames, n_frames))
    return PagingResult("FIFO", hist, faults)


def lru(refs: list[int], n_frames: int) -> PagingResult:
    frames: list[int] = []
    recent: OrderedDict[int, None] = OrderedDict()  # least recently used first
    hist, faults = [], []
    for page in refs:
        fault = page not in frames
        if fault:
            if len(frames) < n_frames:
                frames.append(page)
            else:
                victim, _ = recent.popitem(last=False)
                frames[frames.index(victim)] = page
        recent[page] = None
        recent.move_to_end(page)
        faults.append(fault)
        hist.append(_snapshot(frames, n_frames))
    return PagingResult("LRU", hist, faults)


def optimal(refs: list[int], n_frames: int) -> PagingResult:
    """Belady's optimal algorithm: evict the page used furthest in the future.
    Not implementable in a real OS (needs the future), but it is the lower bound."""
    frames: list[int] = []
    hist, faults = [], []
    for i, page in enumerate(refs):
        fault = page not in frames
        if fault:
            if len(frames) < n_frames:
                frames.append(page)
            else:
                future = refs[i + 1:]
                victim = max(frames, key=lambda f: future.index(f) if f in future else len(future) + 1)
                frames[frames.index(victim)] = page
        faults.append(fault)
        hist.append(_snapshot(frames, n_frames))
    return PagingResult("OPT", hist, faults)


def clock(refs: list[int], n_frames: int) -> PagingResult:
    """Second-chance (clock) algorithm: an approximation of LRU used by real kernels."""
    frames: list[int | None] = [None] * n_frames
    ref_bit = [False] * n_frames
    hand = 0
    hist, faults = [], []
    for page in refs:
        if page in frames:
            ref_bit[frames.index(page)] = True
            faults.append(False)
        else:
            while frames[hand] is not None and ref_bit[hand]:
                ref_bit[hand] = False
                hand = (hand + 1) % n_frames
            frames[hand] = page
            ref_bit[hand] = True
            hand = (hand + 1) % n_frames
            faults.append(True)
        hist.append(list(frames))
    return PagingResult("Clock", hist, faults)


PAGING = {"fifo": fifo, "lru": lru, "opt": optimal, "clock": clock}
