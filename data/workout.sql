BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "library_exercise_enum_values" (
	"id"	INTEGER,
	"metric_type_id"	INTEGER NOT NULL,
	"exercise_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("metric_type_id","exercise_id","value"),
	FOREIGN KEY("exercise_id") REFERENCES "library_exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "library_exercise_metric_overrides" (
	"exercise_metric_id"	INTEGER NOT NULL,
	"input_type"	TEXT,
	"source_type"	TEXT,
	"input_timing"	TEXT,
	"is_required"	BOOLEAN,
	"scope"	TEXT,
	FOREIGN KEY("exercise_metric_id") REFERENCES "library_exercise_metrics"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "library_exercise_metrics" (
	"id"	INTEGER,
	"exercise_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	"position"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "library_exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "library_exercises" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"description"	TEXT,
	"is_user_created"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "library_metric_types" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL UNIQUE,
	"input_type"	TEXT NOT NULL CHECK("input_type" IN ('int', 'float', 'str', 'bool')),
	"source_type"	TEXT NOT NULL CHECK("source_type" IN ('manual_text', 'manual_enum', 'manual_slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('library', 'preset', 'pre_workout', 'post_workout', 'pre_set', 'post_set')),
	"is_required"	BOOLEAN DEFAULT FALSE,
	"scope"	TEXT NOT NULL CHECK("scope" IN ('session', 'section', 'exercise', 'set')),
	"description"	TEXT,
	"is_user_created"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "preset_metadata" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("metric_type_id") REFERENCES "library_metric_types"("id") ON DELETE CASCADE,
	FOREIGN KEY("preset_id") REFERENCES "preset_presets"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_presets" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "preset_section_exercise_metric_enum_values" (
	"id"	INTEGER,
	"section_exercise_metric_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("section_exercise_metric_id") REFERENCES "preset_section_exercise_metrics"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_section_exercise_metrics" (
	"id"	INTEGER,
	"section_exercise_id"	INTEGER NOT NULL,
	"metric_name"	TEXT NOT NULL,
	"input_type"	TEXT NOT NULL,
	"source_type"	TEXT NOT NULL,
	"input_timing"	TEXT NOT NULL,
	"is_required"	BOOLEAN NOT NULL DEFAULT 0,
	"scope"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL DEFAULT 0,
	"library_metric_type_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("section_exercise_id") REFERENCES "preset_section_exercises"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_section_exercises" (
	"id"	INTEGER,
	"section_id"	INTEGER NOT NULL,
	"exercise_name"	TEXT NOT NULL,
	"exercise_description"	TEXT,
	"position"	INTEGER NOT NULL,
	"number_of_sets"	INTEGER NOT NULL DEFAULT 1,
	"library_exercise_id"	INTEGER,
	"rest_time"	INTEGER NOT NULL DEFAULT 120,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("section_id") REFERENCES "preset_sections"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "preset_sections" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "preset_presets"("id") ON DELETE CASCADE
);
CREATE VIEW library_view_exercise_metrics AS
SELECT 
    em.id AS exercise_metric_id,
    em.exercise_id,
    e.name AS exercise_name,
    em.metric_type_id,
    mt.name AS metric_type_name
FROM 
    library_exercise_metrics em
JOIN 
    library_exercises e ON em.exercise_id = e.id
JOIN 
    library_metric_types mt ON em.metric_type_id = mt.id;
CREATE UNIQUE INDEX IF NOT EXISTS "idx_library_exercises_name_user_created" ON "library_exercises" (
	"name",
	"is_user_created"
);
COMMIT;
