import sqlite3
import datetime

DB_PATH = "data/workout.db"  # Change this to your DB file path

def format_timestamp(ts):
    """Convert a stored REAL timestamp to a readable date/time string."""
    if ts is None:
        return "N/A"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all sessions
    cursor.execute("""
        SELECT id, preset_name, started_at, ended_at
        FROM session_sessions
        WHERE deleted = 0
        ORDER BY started_at DESC
    """)
    sessions = cursor.fetchall()

    for session in sessions:
        session_id, preset_name, started_at, ended_at = session
        print(f"\n=== Session: {preset_name} ===")
        print(f"Start: {format_timestamp(started_at)}")
        print(f"End:   {format_timestamp(ended_at)}")

        # Get exercises in this session
        cursor.execute("""
            SELECT id, exercise_name
            FROM session_section_exercises
            WHERE section_id IN (
                SELECT id FROM session_session_sections WHERE session_id = ?
            )
            AND deleted = 0
            ORDER BY position
        """, (session_id,))
        exercises = cursor.fetchall()

        for ex in exercises:
            exercise_id, exercise_name = ex
            print(f"\n  Exercise: {exercise_name}")

            # Get sets for this exercise
            cursor.execute("""
                SELECT id, set_number, started_at, ended_at, notes
                FROM session_exercise_sets
                WHERE section_exercise_id = ?
                AND deleted = 0
                ORDER BY set_number
            """, (exercise_id,))
            sets = cursor.fetchall()

            for s in sets:
                set_id, set_number, start_ts, end_ts, set_notes = s
                if start_ts and end_ts:
                    derived_time = round(end_ts - start_ts, 1)
                else:
                    derived_time = "N/A"

                print(f"    Set {set_number}:")
                print(f"      Start: {format_timestamp(start_ts)}")
                print(f"      End:   {format_timestamp(end_ts)}")
                print(f"      Time:  {derived_time} sec")
                if set_notes:
                    print(f"      Notes: {set_notes}")

                # Get metrics for this set
                cursor.execute("""
                    SELECT sem.metric_name, ssm.value
                    FROM session_set_metrics ssm
                    JOIN session_exercise_metrics sem
                        ON ssm.exercise_metric_id = sem.id
                    WHERE ssm.exercise_set_id = ?
                    AND ssm.deleted = 0
                """, (set_id,))
                metrics = cursor.fetchall()
                for metric_name, value in metrics:
                    print(f"      {metric_name}: {value}")

    conn.close()

if __name__ == "__main__":
    main()