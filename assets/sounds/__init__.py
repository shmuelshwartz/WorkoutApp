from pathlib import Path
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
import time


class SoundSystem:
    """Manage playback of workout sounds.

    Sounds are loaded lazily from the ``assets/sounds`` directory to keep
    memory usage minimal.  The system supports tempo-driven sequences and a
    simple tick-based mode.
    """

    def __init__(self):
        self._base = Path(__file__).resolve().parent
        self._cache: dict[str, object] = {}
        self._event = None
        self._start_event = None
        self._mode = None
        self._sequence: list[str] = []
        self._durations: list[int] = []
        self._index = 0
        self._next_time = 0.0
        # Preload frequently used sounds to avoid first-play latency.
        for name in ("start", "tick"):
            self._load(name)

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    def _load(self, name: str):
        snd = self._cache.get(name)
        if snd is None:
            path = self._base / f"{name}.wav"
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
        if self._event:
            self._event.cancel()
            self._event = None
        if self._start_event:
            self._start_event.cancel()
            self._start_event = None
        self._mode = None

    def _schedule_update(self) -> None:
        if self._event:
            self._event.cancel()
        delay = max(0, self._next_time - time.time())
        self._event = Clock.schedule_once(self._update, delay)

    def start_ticks(self) -> None:
        """Play the tick sound once per second until stopped."""
        self.stop()
        self._mode = "ticks"
        self._next_time = time.time() + 1
        self._schedule_update()

    def start_tempo(self, tempo: str | None, *, skip_start: bool = False) -> None:
        """Begin tempo-driven playback.

        ``tempo`` must be a four digit string. The digits are rotated and used
        as phase durations. If ``tempo`` is invalid, the system falls back to
        tick-based playback.
        """
        if not (tempo and tempo.isdigit() and len(tempo) == 4):
            self.start_ticks()
            return

        rotated = tempo[2:] + tempo[:2]
        self._durations = [int(d) for d in rotated]
        self._sequence = ["start", "hold", "release", "end"]
        self.stop()
        if skip_start:
            base = int(time.time())
            self._mode = "tempo"
            self._index = 1
            self._next_time = base + self._durations[0]
            self._schedule_update()
        else:
            delay = 1 - (time.time() % 1)

            def _begin(dt):
                self.play("start")
                base = int(time.time())
                self._mode = "tempo"
                self._index = 1
                self._next_time = base + self._durations[0]
                self._schedule_update()
                self._start_event = None

            self._start_event = Clock.schedule_once(_begin, delay)

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------
    def _update(self, dt) -> None:
        if self._mode is None:
            return
        now = time.time()
        if now < self._next_time:
            self._schedule_update()
            return
        if self._mode == "ticks":
            self.play("tick")
            self._next_time += 1
        elif self._mode == "tempo":
            name = self._sequence[self._index]
            self.play(name)
            dur = self._durations[self._index]
            self._index = (self._index + 1) % len(self._sequence)
            self._next_time += dur
        self._schedule_update()
