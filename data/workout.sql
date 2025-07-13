BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "exercise_enum_values" (
	"id"	INTEGER,
	"metric_type_id"	INTEGER NOT NULL,
	"exercise_id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	UNIQUE("metric_type_id","exercise_id","value"),
	FOREIGN KEY("exercise_id") REFERENCES "exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "exercise_metrics" (
	"id"	INTEGER,
	"exercise_id"	INTEGER NOT NULL,
	"metric_type_id"	INTEGER NOT NULL,
	"position"	INTEGER DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "exercises"("id") ON DELETE CASCADE,
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "exercises" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"description"	TEXT,
	"is_user_created"	BOOLEAN NOT NULL DEFAULT 0,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "metric_types" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL UNIQUE,
	"input_type"	TEXT NOT NULL CHECK("input_type" IN ('int', 'float', 'str', 'bool')),
	"source_type"	TEXT NOT NULL CHECK("source_type" IN ('manual_text', 'manual_enum', 'manual_slider')),
	"input_timing"	TEXT NOT NULL CHECK("input_timing" IN ('preset', 'pre_workout', 'post_workout', 'pre_set', 'post_set')),
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
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE,
	FOREIGN KEY("preset_id") REFERENCES "presets"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "presets" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "section_exercise_metrics" (
	"id"	INTEGER,
	"section_exercise_id"	INT NOT NULL,
	"metric_type_id"	INT NOT NULL,
	"input_timing"	TEXT NOT NULL,
	"is_required"	NUM NOT NULL DEFAULT 0,
	"scope"	TEXT NOT NULL,
	"default_exercise_metric_id"	INT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("metric_type_id") REFERENCES "metric_types"("id") ON DELETE CASCADE,
	FOREIGN KEY("section_exercise_id") REFERENCES "section_exercises"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "section_exercises" (
	"id"	INTEGER,
	"section_id"	INTEGER NOT NULL,
	"exercise_id"	INTEGER NOT NULL,
	"position"	INTEGER NOT NULL,
	"number_of_sets"	INTEGER NOT NULL DEFAULT 1,
	"exercise_name"	TEXT,
	"exercise_description"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("exercise_id") REFERENCES "exercises"("id"),
	FOREIGN KEY("section_id") REFERENCES "sections"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "sections" (
	"id"	INTEGER,
	"preset_id"	INTEGER NOT NULL,
	"name"	TEXT NOT NULL,
	"position"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("preset_id") REFERENCES "presets"("id") ON DELETE CASCADE
);
CREATE VIEW view_exercise_metrics AS
SELECT 
    em.id AS exercise_metric_id,
    em.exercise_id,
    e.name AS exercise_name,
    em.metric_type_id,
    mt.name AS metric_type_name
FROM 
    exercise_metrics em
JOIN 
    exercises e ON em.exercise_id = e.id
JOIN 
    metric_types mt ON em.metric_type_id = mt.id;
COMMIT;
