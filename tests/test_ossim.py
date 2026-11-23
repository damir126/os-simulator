import unittest

from ossim import deadlock
from ossim.memory import clock, fifo, lru, optimal
from ossim.scheduling import Process, fcfs, priority, round_robin, sjf, srtf

# Classic textbook example (Silberschatz), all arrive at 0
BASIC = [Process("P1", 0, 24), Process("P2", 0, 3), Process("P3", 0, 3)]
STAGGERED = [Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 9), Process("P4", 3, 5)]


class SchedulingTests(unittest.TestCase):
    def test_fcfs_convoy_effect(self):
        s = fcfs(BASIC)
        self.assertEqual([(x.pid, x.start, x.end) for x in s.gantt], [("P1", 0, 24), ("P2", 24, 27), ("P3", 27, 30)])
        self.assertEqual(s.averages(BASIC)["avg_waiting"], 17)

    def test_sjf_is_better_here(self):
        self.assertEqual(sjf(BASIC).averages(BASIC)["avg_waiting"], 3)

    def test_srtf_textbook(self):
        s = srtf(STAGGERED)
        self.assertEqual([x.pid for x in s.gantt], ["P1", "P2", "P4", "P1", "P3"])
        self.assertEqual(s.averages(STAGGERED)["avg_waiting"], 6.5)

    def test_round_robin(self):
        s = round_robin(BASIC, quantum=4)
        self.assertEqual([x.pid for x in s.gantt], ["P1", "P2", "P3", "P1"])
        self.assertAlmostEqual(s.averages(BASIC)["avg_waiting"], 5.67, places=2)

    def test_priority(self):
        procs = [Process("A", 0, 10, 3), Process("B", 0, 1, 1), Process("C", 0, 2, 4),
                 Process("D", 0, 1, 5), Process("E", 0, 5, 2)]
        s = priority(procs)
        self.assertEqual([x.pid for x in s.gantt], ["B", "E", "A", "C", "D"])
        self.assertEqual(s.averages(procs)["avg_waiting"], 8.2)

    def test_idle_time(self):
        procs = [Process("A", 0, 2), Process("B", 5, 1)]
        s = fcfs(procs)
        self.assertEqual([x.pid for x in s.gantt], ["A", "idle", "B"])
        self.assertEqual(s.averages(procs)["cpu_utilization"], 50.0)

    def test_all_work_is_done(self):
        for algo in (fcfs, sjf, srtf, priority, lambda p: round_robin(p, 3)):
            s = algo(STAGGERED)
            busy = sum(x.end - x.start for x in s.gantt if x.pid != "idle")
            self.assertEqual(busy, sum(p.burst for p in STAGGERED))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            Process("X", 0, 0)
        with self.assertRaises(ValueError):
            fcfs([Process("A", 0, 1), Process("A", 1, 1)])


class PagingTests(unittest.TestCase):
    REFS = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1]

    def test_textbook_fault_counts(self):
        self.assertEqual(fifo(self.REFS, 3).fault_count, 15)
        self.assertEqual(lru(self.REFS, 3).fault_count, 12)
        self.assertEqual(optimal(self.REFS, 3).fault_count, 9)

    def test_belady_anomaly(self):
        refs = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        self.assertEqual(fifo(refs, 3).fault_count, 9)
        self.assertEqual(fifo(refs, 4).fault_count, 10)  # more frames, more faults!

    def test_clock_between_fifo_and_opt(self):
        c = clock(self.REFS, 3).fault_count
        self.assertLessEqual(optimal(self.REFS, 3).fault_count, c)


class BankerTests(unittest.TestCase):
    def setUp(self):
        self.available = [3, 3, 2]
        self.maximum = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
        self.allocation = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]

    def test_safe_state(self):
        safe, seq = deadlock.is_safe(self.available, self.maximum, self.allocation)
        self.assertTrue(safe)
        self.assertEqual(seq, [1, 3, 4, 0, 2])

    def test_requests(self):
        self.assertTrue(deadlock.request(self.available, self.maximum, self.allocation, 1, [1, 0, 2]))
        self.assertEqual(self.available, [2, 3, 0])
        self.assertFalse(deadlock.request(self.available, self.maximum, self.allocation, 4, [3, 3, 0]))
        self.assertFalse(deadlock.request(self.available, self.maximum, self.allocation, 0, [0, 2, 0]))


if __name__ == "__main__":
    unittest.main()
