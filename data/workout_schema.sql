BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "library_exercise_metrics" (
	"id"	INTEGER,
	"exercise_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	"type"	TEXT CHECK("type" IS NULL OR "type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT CHECK("input_timing" IS NULL OR "input_timing" IN ('library', 'preset', 'pre_session', 'post_session', 'pre_exercise', 'post_exercise', 'pre_set', 'post_set')),
	"scope"	TEXT CHECK("scope" IS NULL OR "scope" IN ('exercise', 'set')),
	"is_required"	BOOLEAN,
	"enum_values_json"	TEXT,
	"position"	INTEGER DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	"value"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "library_exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "library_exercises" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"description"	TEXT,
	"is_user_created"	BOOLEAN NOT NULL DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "library_metric_types" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"description"	TEXT,
	"type"	TEXT NOT NULL CHECK("type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('library', 'preset', 'pre_session', 'post_session', 'pre_exercise', 'post_exercise', 'pre_set', 'post_set')),
	"scope"	TEXT NOT NULL CHECK("scope" IN ('preset', 'session', 'exercise', 'set')),
	"is_required"	BOOLEAN DEFAULT FALSE,
	"enum_values_json"	TEXT,
	"is_user_created"	BOOLEAN NOT NULL DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "preset_exercise_metrics" (
	"id"	INTEGER,
	"section_exercise_id"	INTEGER NOT NULL,
	"library_metric_type_id"	INTEGER,
	"metric_name"	TEXT NOT NULL,
	"metric_description"	TEXT,
	"type"	TEXT NOT NULL CHECK("type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('preset', 'pre_session', 'post_session', 'pre_exercise', 'post_exercise', 'pre_set', 'post_set')),
	"scope"	TEXT NOT NULL CHECK("scope" IN ('exercise', 'set')),
	"is_required"	BOOLEAN NOT NULL DEFAULT 0,
	"enum_values_json"	TEXT,
	"position"	INTEGER NOT NULL DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	"value"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE SET NULL,
	FOREIGN KEY("section_exercise_id") REFERENCES "preset_section_exercises"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_preset_metrics" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"library_metric_type_id"	INTEGER,
	"metric_name"	TEXT NOT NULL,
	"metric_description"	TEXT,
	"type"	TEXT NOT NULL CHECK("type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('library', 'preset', 'pre_session', 'post_session')),
	"scope"	TEXT NOT NULL CHECK("scope" IN ('preset', 'session')),
	"is_required"	BOOLEAN NOT NULL DEFAULT 0,
	"enum_values_json"	TEXT,
	"position"	INTEGER DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	"value"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE SET NULL,
	FOREIGN KEY("preset_id") REFERENCES "preset_presets"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_preset_sections" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "preset_presets"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_presets" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"position"	INTEGER DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "preset_section_exercises" (
	"id"	INTEGER,
	"section_id"	INTEGER NOT NULL,
	"library_exercise_id"	INTEGER,
	"exercise_name"	TEXT NOT NULL,
	"exercise_description"	TEXT,
	"number_of_sets"	INTEGER NOT NULL DEFAULT 1,
	"rest_time"	INTEGER NOT NULL DEFAULT 120,
	"position"	INTEGER NOT NULL,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_exercise_id") REFERENCES "library_exercises"("id") ON DELETE SET NULL,
	FOREIGN KEY("section_id") REFERENCES "preset_preset_sections"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_exercise_metrics" (
	"id"	INTEGER,
	"session_exercise_id"	INTEGER NOT NULL,
	"library_metric_type_id"	INTEGER,
	"preset_exercise_metric_id"	INTEGER,
	"metric_name"	TEXT NOT NULL,
	"metric_description"	TEXT,
	"type"	TEXT NOT NULL CHECK("type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('preset', 'pre_session', 'post_session', 'pre_exercise', 'post_exercise', 'pre_set', 'post_set')),
	"scope"	TEXT NOT NULL CHECK("scope" IN ('exercise', 'set')),
	"is_required"	BOOLEAN NOT NULL DEFAULT 0,
	"enum_values_json"	TEXT,
	"value"	TEXT,
	"notes"	TEXT,
	"position"	INTEGER NOT NULL DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE SET NULL,
	FOREIGN KEY("preset_exercise_metric_id") REFERENCES "preset_exercise_metrics"("id") ON DELETE SET NULL,
	FOREIGN KEY("session_exercise_id") REFERENCES "session_section_exercises"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_exercise_sets" (
	"id"	INTEGER,
	"section_exercise_id"	INTEGER NOT NULL,
	"set_number"	INTEGER NOT NULL,
	"started_at"	REAL,
	"ended_at"	REAL,
	"notes"	TEXT,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("section_exercise_id") REFERENCES "session_section_exercises"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_section_exercises" (
	"id"	INTEGER,
	"section_id"	INTEGER NOT NULL,
	"library_exercise_id"	INTEGER,
	"preset_section_exercise_id"	INTEGER,
	"exercise_name"	TEXT NOT NULL,
	"exercise_description"	TEXT,
	"number_of_sets"	INTEGER NOT NULL DEFAULT 1,
	"rest_time"	INTEGER NOT NULL DEFAULT 120,
	"notes"	TEXT,
	"position"	INTEGER NOT NULL,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_exercise_id") REFERENCES "library_exercises"("id") ON DELETE SET NULL,
	FOREIGN KEY("preset_section_exercise_id") REFERENCES "preset_section_exercises"("id") ON DELETE SET NULL,
	FOREIGN KEY("section_id") REFERENCES "session_session_sections"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_session_metrics" (
	"id"	INTEGER,
	"session_id"	INTEGER NOT NULL,
	"library_metric_type_id"	INTEGER,
	"preset_preset_metric_id"	INTEGER,
	"metric_name"	TEXT NOT NULL,
	"metric_description"	TEXT,
	"type"	TEXT NOT NULL CHECK("type" IN ('int', 'float', 'str', 'bool', 'enum', 'slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('library', 'preset', 'pre_session', 'post_session', 'pre_exercise', 'post_exercise', 'pre_set', 'post_set')),
	"scope"	TEXT NOT NULL CHECK("scope" IN ('preset', 'session')),
	"is_required"	BOOLEAN NOT NULL DEFAULT 0,
	"enum_values_json"	TEXT,
	"value"	TEXT,
	"notes"	TEXT,
	"position"	INTEGER NOT NULL DEFAULT 0,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("library_metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE SET NULL,
	FOREIGN KEY("preset_preset_metric_id") REFERENCES "preset_preset_metrics"("id") ON DELETE SET NULL,
	FOREIGN KEY("session_id") REFERENCES "session_sessions"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_session_sections" (
	"id"	INTEGER,
	"session_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"notes"	TEXT,
	"position"	INTEGER NOT NULL,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("session_id") REFERENCES "session_sessions"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "session_sessions" (
	"id"	INTEGER,
	"preset_id"	INTEGER,
	"preset_name"	TEXT NOT NULL,
	"started_at"	REAL NOT NULL,
	"ended_at"	REAL,
	"notes"	TEXT,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "preset_presets"("id") ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS "session_set_metrics" (
	"id"	INTEGER,
	"exercise_set_id"	INTEGER NOT NULL,
	"exercise_metric_id"	INTEGER NOT NULL,
	"value"	TEXT,
	"notes"	TEXT,
	"deleted"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_metric_id") REFERENCES "session_exercise_metrics"("id") ON DELETE CASCADE,
	FOREIGN KEY("exercise_set_id") REFERENCES "session_exercise_sets"("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "idx_library_exercise_metric_unique_active" ON "library_exercise_metrics" (
	"exercise_id",
	"metric_type_id"
) WHERE "deleted" = 0;
CREATE UNIQUE INDEX IF NOT EXISTS "idx_library_exercises_name_user_created" ON "library_exercises" (
	"name",
	"is_user_created"
);
CREATE UNIQUE INDEX IF NOT EXISTS "idx_library_metric_types_name_user_created" ON "library_metric_types" (
	"name",
	"is_user_created"
);
CREATE UNIQUE INDEX IF NOT EXISTS "idx_unique_exercise_metric_active" ON "preset_exercise_metrics" (
	"section_exercise_id",
	"metric_name"
) WHERE "deleted" = 0;
CREATE UNIQUE INDEX IF NOT EXISTS "idx_unique_preset_metric_active" ON "preset_preset_metrics" (
	"preset_id",
	"library_metric_type_id"
) WHERE "deleted" = 0;
COMMIT;
