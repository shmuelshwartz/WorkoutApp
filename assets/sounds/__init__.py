from pathlib import Path
from kivy.core.audio import SoundLoader
from kivy.clock import Clock


class SoundSystem:
    """Manage playback of workout sounds.

    Sounds are loaded lazily from the ``assets/sounds`` directory to keep
    memory usage minimal.  The system supports tempo-driven sequences and a
    simple tick-based mode.
    """

    def __init__(self):
        self._base = Path(__file__).resolve().parent
        self._cache: dict[str, object] = {}
        self._events: list = []
        self._tick_event = None

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    def _load(self, name: str):
        snd = self._cache.get(name)
        if snd is None:
            path = self._base / f"{name}.mp3"
            snd = SoundLoader.load(str(path))
            self._cache[name] = snd
        return snd

    def play(self, name: str) -> None:
        """Play a named sound if available."""
        snd = self._load(name)
        if snd:
            snd.stop()
            snd.play()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def stop(self) -> None:
        """Cancel any scheduled playback."""
        for ev in self._events:
            ev.cancel()
        self._events.clear()
        if self._tick_event:
            self._tick_event.cancel()
            self._tick_event = None

    def start_ticks(self) -> None:
        """Play the tick sound once per second until stopped."""
        self.stop()
        self._tick_event = Clock.schedule_interval(lambda dt: self.play("tick"), 1)

    def start_tempo(self, tempo: str | None, *, skip_start: bool = False) -> None:
        """Begin tempo-driven playback.

        ``tempo`` must be a four digit string.  The digits are rotated and used
        as phase durations.  If ``tempo`` is invalid, the system falls back to
        tick-based playback.
        """
        if not (tempo and tempo.isdigit() and len(tempo) == 4):
            self.start_ticks()
            return

        rotated = tempo[2:] + tempo[:2]
        durations = [int(d) for d in rotated]
        sequence = ["start", "hold", "release", "end"]
        self.stop()
        total = sum(durations)

        delay = 0
        phases = sequence
        durs = durations
        if skip_start:
            delay = durs[0]
            phases = sequence[1:]
            durs = durations[1:]
        else:
            self._events.append(Clock.schedule_once(lambda dt: self.play("start"), 0))
            delay = durs[0]
            phases = sequence[1:]
            durs = durations[1:]

        for name, dur in zip(phases, durs):
            self._events.append(Clock.schedule_once(lambda dt, n=name: self.play(n), delay))
            delay += dur

        # restart the cycle with start sound
        self._events.append(Clock.schedule_once(lambda dt: self.start_tempo(tempo), total))
