BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "exercise_metrics" (
	"id"	INTEGER,
	"exercise_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "exercises" (
	"id"	INTEGER,
	"section_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("section_id") REFERENCES "sections"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "metric_types" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL UNIQUE,
	"input_type"	TEXT NOT NULL CHECK("input_type" IN ('int', 'float', 'str', 'bool')),
	"source_type"	TEXT NOT NULL CHECK("source_type" IN ('manual_text', 'manual_enum', 'manual_slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('preset', 'pre_workout', 'post_workout', 'pre_set', 'post_set')),
	"is_required"	BOOLEAN DEFAULT FALSE,
	"scope"	TEXT NOT NULL CHECK("scope" IN ('session', 'section', 'exercise', 'set')),
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "presets" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "sections" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "presets"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_defined_enum_values" (
	"id"	INTEGER,
	"metric_type_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "workout_exercise_entries" (
	"id"	INTEGER,
	"session_id"	INTEGER NOT NULL,
	"exercise_id"	INTEGER NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "exercises"("id"),
	FOREIGN KEY("session_id") REFERENCES "workout_sessions"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "workout_metric_values" (
	"id"	INTEGER,
	"exercise_entry_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_entry_id") REFERENCES "workout_exercise_entries"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id")
);
CREATE TABLE IF NOT EXISTS "workout_sessions" (
	"id"	INTEGER,
	"preset_id"	INTEGER,
	"start_time"	DATETIME,
	"end_time"	DATETIME,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "presets"("id")
);
COMMIT;
