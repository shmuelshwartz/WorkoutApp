# AGENTS - Sound System

## Purpose
The sound system provides audio cues during workouts. It synchronizes with exercise tempo and rest timers, helping the user maintain rhythm and stay aware of timing without watching the screen.

## Sound Types
The system uses five main sounds:
- `start.mp3` – signals the beginning of a movement or set
- `hold.mp3` – signals the pause/hold portion of a movement
- `release.mp3` – signals the controlled release/return portion
- `end.mp3` – signals the completion of the movement
- `tick.mp3` – a simple ticking sound, used for countdowns and tick-based exercises

## Tempo System
### Type 1: Tempo-Driven (4-digit tempo only)
Exercises use a 4-digit tempo string (e.g. "1234"). The system rotates the string so that it becomes "3412". Playback then follows this sequence:

Start sound → wait 3 seconds (1st digit of rotated string).
Hold sound → wait 4 seconds (2nd digit).
Release sound → wait 1 second (3rd digit).
End sound → wait 2 seconds (4th digit).
Return to Start and repeat the cycle.

Example:
Input tempo: "1234"
Rotated tempo: "3412"
Playback: start → (3s) → hold → (4s) → release → (1s) → end → (2s) → start → repeat.

### Type 2: Tick-Based
Instead of tempo phases, plays `tick.mp3` once per second. Used for exercises where the user wants to count time or repetitions without fixed tempo. Runs continuously until the set ends.

## Rest Timer System
During the rest screen:
- In the last 10 seconds of the countdown, if the Ready button is active: play `tick.mp3` once per second.
- On the final second (when the timer reaches 0), do not play a tick. Instead, play `start.mp3` to signal the beginning of the next set.

## Rules & Behavior
- Sound only plays when the Ready button has been pressed (user opted in).
- Tempo-driven playback applies only to valid 4-digit numeric tempo strings.
- All sounds must be short and distinct to avoid confusion.
- The system must seamlessly loop for tempo exercises until the set is finished.
- Rest countdown ticks must always end with `start.mp3`, never with another tick.

## Implementation Notes
- Location: `assets/sounds/`
- File naming must match the sound types listed above.
- The system should be modular, so new sound types can be added without breaking existing logic.
- If no tempo is defined for an exercise, fallback behavior is tick-based timing.
