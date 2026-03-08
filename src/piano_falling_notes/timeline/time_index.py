import bisect

from .models import RenderNote


class TimeIndex:
    """Binary-search index for O(log N + K) time-range queries."""

    def __init__(self, notes: list[RenderNote]) -> None:
        # Sort by start time; keep a parallel list of end times for filtering.
        self._notes = sorted(notes, key=lambda n: n.start_seconds)
        self._starts = [n.start_seconds for n in self._notes]
        self._ends = [n.start_seconds + n.duration_seconds for n in self._notes]

    def query(self, view_top_time: float, view_bottom_time: float) -> list[RenderNote]:
        """Return notes visible in [view_top_time, view_bottom_time).

        A note is visible when:
            note.start_seconds < view_bottom_time
            AND note.start_seconds + note.duration_seconds > view_top_time
        """
        # All notes that start before view_bottom_time
        upper = bisect.bisect_left(self._starts, view_bottom_time)

        result = []
        for i in range(upper):
            if self._ends[i] > view_top_time:
                result.append(self._notes[i])
        return result
