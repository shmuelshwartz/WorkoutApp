from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TempoPhase:
    """Represents a single phase in the tempo cycle."""

    name: str
    duration: int


class TempoCycle:
    """Utility for computing tempo phase progression.

    A tempo is a four digit string describing [eccentric, pause bottom,
    concentric, pause top] durations. Execution always begins with the
    concentric phase, i.e. the third digit.
    """

    ORDER_NAMES: List[str] = [
        "concentric",
        "pause_top",
        "eccentric",
        "pause_bottom",
    ]

    def __init__(self, tempo: str) -> None:
        if len(tempo) != 4 or not tempo.isdigit():
            raise ValueError("Tempo must be a four digit string")

        digits = [int(ch) for ch in tempo]
        order = [2, 3, 0, 1]  # start from concentric
        self.phases: List[TempoPhase] = [
            TempoPhase(self.ORDER_NAMES[i], digits[idx]) for i, idx in enumerate(order)
        ]
        self.total: int = sum(p.duration for p in self.phases)

    def phase_at(self, elapsed: float) -> Tuple[int, float, float]:
        """Return current phase index, fraction complete, and remaining time.

        ``elapsed`` is seconds since cycle start. The cycle loops when
        ``elapsed`` exceeds the total duration.
        """

        if self.total == 0:
            return 0, 0.0, 0.0

        t = elapsed % self.total
        acc = 0
        for index, phase in enumerate(self.phases):
            next_acc = acc + phase.duration
            if t < next_acc:
                within = t - acc
                fraction = within / phase.duration if phase.duration else 1.0
                remaining = self.total - (acc + within)
                return index, fraction, remaining
            acc = next_acc

        # Should not reach here, but return last phase complete
        return len(self.phases) - 1, 1.0, 0.0
