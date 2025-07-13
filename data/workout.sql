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
CREATE TABLE IF NOT EXISTS "user_defined_enum_values" (
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
INSERT INTO "exercise_metrics" VALUES (1,1,5);
INSERT INTO "exercise_metrics" VALUES (2,2,5);
INSERT INTO "exercise_metrics" VALUES (3,3,5);
INSERT INTO "exercise_metrics" VALUES (4,4,5);
INSERT INTO "exercise_metrics" VALUES (5,5,5);
INSERT INTO "exercise_metrics" VALUES (6,6,5);
INSERT INTO "exercise_metrics" VALUES (7,7,5);
INSERT INTO "exercise_metrics" VALUES (8,8,5);
INSERT INTO "exercise_metrics" VALUES (9,9,5);
INSERT INTO "exercise_metrics" VALUES (10,1,3);
INSERT INTO "exercise_metrics" VALUES (11,2,3);
INSERT INTO "exercise_metrics" VALUES (12,3,3);
INSERT INTO "exercise_metrics" VALUES (13,4,3);
INSERT INTO "exercise_metrics" VALUES (14,5,3);
INSERT INTO "exercise_metrics" VALUES (15,6,3);
INSERT INTO "exercise_metrics" VALUES (16,7,3);
INSERT INTO "exercise_metrics" VALUES (17,8,3);
INSERT INTO "exercise_metrics" VALUES (18,9,3);
INSERT INTO "exercise_metrics" VALUES (19,1,1);
INSERT INTO "exercise_metrics" VALUES (20,1,4);
INSERT INTO "exercise_metrics" VALUES (21,2,6);
INSERT INTO "exercise_metrics" VALUES (22,2,1);
INSERT INTO "exercise_metrics" VALUES (23,2,4);
INSERT INTO "exercise_metrics" VALUES (24,2,2);
INSERT INTO "exercise_metrics" VALUES (25,3,6);
INSERT INTO "exercise_metrics" VALUES (26,3,1);
INSERT INTO "exercise_metrics" VALUES (27,3,4);
INSERT INTO "exercise_metrics" VALUES (28,3,2);
INSERT INTO "exercise_metrics" VALUES (29,4,7);
INSERT INTO "exercise_metrics" VALUES (30,5,1);
INSERT INTO "exercise_metrics" VALUES (31,5,4);
INSERT INTO "exercise_metrics" VALUES (32,6,6);
INSERT INTO "exercise_metrics" VALUES (33,6,1);
INSERT INTO "exercise_metrics" VALUES (34,6,4);
INSERT INTO "exercise_metrics" VALUES (35,6,2);
INSERT INTO "exercise_metrics" VALUES (36,7,1);
INSERT INTO "exercise_metrics" VALUES (37,7,4);
INSERT INTO "exercise_metrics" VALUES (38,7,2);
INSERT INTO "exercise_metrics" VALUES (39,8,1);
INSERT INTO "exercise_metrics" VALUES (40,8,4);
INSERT INTO "exercise_metrics" VALUES (41,8,2);
INSERT INTO "exercise_metrics" VALUES (42,9,1);
INSERT INTO "exercise_metrics" VALUES (43,9,4);
INSERT INTO "exercise_metrics" VALUES (44,9,2);
INSERT INTO "exercises" VALUES (1,'Push-ups','Bodyweight pressing exercise',0);
INSERT INTO "exercises" VALUES (2,'Bench Press','Barbell pressing exercise',0);
INSERT INTO "exercises" VALUES (3,'Overhead Press','Barbell overhead pressing',0);
INSERT INTO "exercises" VALUES (4,'Front Lever','Advanced static hold pulling exercise',1);
INSERT INTO "exercises" VALUES (5,'Pull-ups','Bodyweight pulling exercise',0);
INSERT INTO "exercises" VALUES (6,'Barbell Rows','Barbell pulling exercise',0);
INSERT INTO "exercises" VALUES (7,'Squats','Barbell lower body compound lift',0);
INSERT INTO "exercises" VALUES (8,'Deadlifts','Barbell hip hinge and pulling lift',0);
INSERT INTO "exercises" VALUES (9,'Lunges','Unilateral leg exercise',0);
INSERT INTO "exercises" VALUES (10,'Shoulder Circles','Simple dynamic warm-up for shoulder mobility',1);
INSERT INTO "exercises" VALUES (11,'Jumping Jacks','Cardio warm-up exercise',1);
INSERT INTO "exercises" VALUES (12,'Skipping Rope','Jump rope warm-up exercise',1);
INSERT INTO "metric_types" VALUES (1,'Reps','int','manual_text','post_set',1,'set','Number of repetitions performed in a set',0);
INSERT INTO "metric_types" VALUES (2,'Weight (kg)','float','manual_text','pre_set',1,'set','Weight lifted in kilograms',0);
INSERT INTO "metric_types" VALUES (3,'RPE','float','manual_slider','post_set',0,'set','Rate of Perceived Exertion (scale 1-10)',0);
INSERT INTO "metric_types" VALUES (4,'Tempo','str','manual_text','preset',0,'exercise','Movement tempo, e.g., "21X1"',0);
INSERT INTO "metric_types" VALUES (5,'Notes','str','manual_text','post_set',0,'set','Free-text notes about the set or exercise',0);
INSERT INTO "metric_types" VALUES (6,'Machine','str','manual_enum','preset',0,'exercise','Equipment or machine used',0);
INSERT INTO "metric_types" VALUES (7,'Progression','str','manual_enum','post_set',1,'set','Exercise progression status or variation',1);
INSERT INTO "metric_types" VALUES (8,'Test','float','manual_text','post_workout',0,'set','This is just a test to see if i can create a new metric',1);
INSERT INTO "presets" VALUES (1,'Push Day');
INSERT INTO "presets" VALUES (2,'Pull Day');
INSERT INTO "presets" VALUES (3,'Leg Day');
INSERT INTO "section_exercise_metrics" VALUES (1,4,5,'post_set',0,'set',1);
INSERT INTO "section_exercise_metrics" VALUES (2,5,5,'post_set',0,'set',2);
INSERT INTO "section_exercise_metrics" VALUES (3,6,5,'post_set',0,'set',3);
INSERT INTO "section_exercise_metrics" VALUES (4,7,5,'post_set',0,'set',4);
INSERT INTO "section_exercise_metrics" VALUES (5,8,5,'post_set',0,'set',5);
INSERT INTO "section_exercise_metrics" VALUES (6,9,5,'post_set',0,'set',6);
INSERT INTO "section_exercise_metrics" VALUES (7,10,5,'post_set',0,'set',7);
INSERT INTO "section_exercise_metrics" VALUES (8,11,5,'post_set',0,'set',8);
INSERT INTO "section_exercise_metrics" VALUES (9,12,5,'post_set',0,'set',9);
INSERT INTO "section_exercise_metrics" VALUES (10,4,3,'post_set',0,'set',10);
INSERT INTO "section_exercise_metrics" VALUES (11,5,3,'post_set',0,'set',11);
INSERT INTO "section_exercise_metrics" VALUES (12,6,3,'post_set',0,'set',12);
INSERT INTO "section_exercise_metrics" VALUES (13,7,3,'post_set',0,'set',13);
INSERT INTO "section_exercise_metrics" VALUES (14,8,3,'post_set',0,'set',14);
INSERT INTO "section_exercise_metrics" VALUES (15,9,3,'post_set',0,'set',15);
INSERT INTO "section_exercise_metrics" VALUES (16,10,3,'post_set',0,'set',16);
INSERT INTO "section_exercise_metrics" VALUES (17,11,3,'post_set',0,'set',17);
INSERT INTO "section_exercise_metrics" VALUES (18,12,3,'post_set',0,'set',18);
INSERT INTO "section_exercise_metrics" VALUES (19,4,1,'post_set',1,'set',19);
INSERT INTO "section_exercise_metrics" VALUES (20,4,4,'preset',0,'exercise',20);
INSERT INTO "section_exercise_metrics" VALUES (21,5,6,'preset',0,'exercise',21);
INSERT INTO "section_exercise_metrics" VALUES (22,5,1,'post_set',1,'set',22);
INSERT INTO "section_exercise_metrics" VALUES (23,5,4,'preset',0,'exercise',23);
INSERT INTO "section_exercise_metrics" VALUES (24,5,2,'pre_set',1,'set',24);
INSERT INTO "section_exercise_metrics" VALUES (25,6,6,'preset',0,'exercise',25);
INSERT INTO "section_exercise_metrics" VALUES (26,6,1,'post_set',1,'set',26);
INSERT INTO "section_exercise_metrics" VALUES (27,6,4,'preset',0,'exercise',27);
INSERT INTO "section_exercise_metrics" VALUES (28,6,2,'pre_set',1,'set',28);
INSERT INTO "section_exercise_metrics" VALUES (29,7,7,'post_set',1,'set',29);
INSERT INTO "section_exercise_metrics" VALUES (30,8,1,'post_set',1,'set',30);
INSERT INTO "section_exercise_metrics" VALUES (31,8,4,'preset',0,'exercise',31);
INSERT INTO "section_exercise_metrics" VALUES (32,9,6,'preset',0,'exercise',32);
INSERT INTO "section_exercise_metrics" VALUES (33,9,1,'post_set',1,'set',33);
INSERT INTO "section_exercise_metrics" VALUES (34,9,4,'preset',0,'exercise',34);
INSERT INTO "section_exercise_metrics" VALUES (35,9,2,'pre_set',1,'set',35);
INSERT INTO "section_exercise_metrics" VALUES (36,10,1,'post_set',1,'set',36);
INSERT INTO "section_exercise_metrics" VALUES (37,10,4,'preset',0,'exercise',37);
INSERT INTO "section_exercise_metrics" VALUES (38,10,2,'pre_set',1,'set',38);
INSERT INTO "section_exercise_metrics" VALUES (39,11,1,'post_set',1,'set',39);
INSERT INTO "section_exercise_metrics" VALUES (40,11,4,'preset',0,'exercise',40);
INSERT INTO "section_exercise_metrics" VALUES (41,11,2,'pre_set',1,'set',41);
INSERT INTO "section_exercise_metrics" VALUES (42,12,1,'post_set',1,'set',42);
INSERT INTO "section_exercise_metrics" VALUES (43,12,4,'preset',0,'exercise',43);
INSERT INTO "section_exercise_metrics" VALUES (44,12,2,'pre_set',1,'set',44);
INSERT INTO "section_exercises" VALUES (1,1,10,1,3,'Shoulder Circles','Simple dynamic warm-up for shoulder mobility');
INSERT INTO "section_exercises" VALUES (2,3,11,1,3,'Jumping Jacks','Cardio warm-up exercise');
INSERT INTO "section_exercises" VALUES (3,5,12,1,3,'Skipping Rope','Jump rope warm-up exercise');
INSERT INTO "section_exercises" VALUES (4,2,1,1,3,'Push-ups','Bodyweight pressing exercise');
INSERT INTO "section_exercises" VALUES (5,2,2,2,3,'Bench Press','Barbell pressing exercise');
INSERT INTO "section_exercises" VALUES (6,2,3,3,3,'Overhead Press','Barbell overhead pressing');
INSERT INTO "section_exercises" VALUES (7,4,4,1,3,'Front Lever','Advanced static hold pulling exercise');
INSERT INTO "section_exercises" VALUES (8,4,5,2,3,'Pull-ups','Bodyweight pulling exercise');
INSERT INTO "section_exercises" VALUES (9,4,6,3,3,'Barbell Rows','Barbell pulling exercise');
INSERT INTO "section_exercises" VALUES (10,6,7,1,3,'Squats','Barbell lower body compound lift');
INSERT INTO "section_exercises" VALUES (11,6,8,2,3,'Deadlifts','Barbell hip hinge and pulling lift');
INSERT INTO "section_exercises" VALUES (12,6,9,3,3,'Lunges','Unilateral leg exercise');
INSERT INTO "sections" VALUES (1,1,'Warm-up',1);
INSERT INTO "sections" VALUES (2,1,'Workout',2);
INSERT INTO "sections" VALUES (3,2,'Warm-up',1);
INSERT INTO "sections" VALUES (4,2,'Workout',2);
INSERT INTO "sections" VALUES (5,3,'Warm-up',1);
INSERT INTO "sections" VALUES (6,3,'Workout',2);
INSERT INTO "user_defined_enum_values" VALUES (1,6,2,'Flat Barbell Bench',1);
INSERT INTO "user_defined_enum_values" VALUES (2,6,2,'Incline Smith Machine',2);
INSERT INTO "user_defined_enum_values" VALUES (3,6,2,'Hammer Strength Chest Press',3);
INSERT INTO "user_defined_enum_values" VALUES (4,6,3,'Smith Machine Overhead Press',1);
INSERT INTO "user_defined_enum_values" VALUES (5,6,3,'Seated Shoulder Press Machine',2);
INSERT INTO "user_defined_enum_values" VALUES (6,6,3,'Hammer Strength Overhead Press',3);
INSERT INTO "user_defined_enum_values" VALUES (7,6,6,'Hammer Strength Row',1);
INSERT INTO "user_defined_enum_values" VALUES (8,6,6,'T-Bar Row Machine',2);
INSERT INTO "user_defined_enum_values" VALUES (9,6,6,'Seated Cable Row Machine',3);
INSERT INTO "user_defined_enum_values" VALUES (10,7,4,'Tuck',1);
INSERT INTO "user_defined_enum_values" VALUES (11,7,4,'Advanced Tuck',2);
INSERT INTO "user_defined_enum_values" VALUES (12,7,4,'Half Lay',3);
INSERT INTO "user_defined_enum_values" VALUES (13,7,4,'Straddle',4);
INSERT INTO "user_defined_enum_values" VALUES (14,7,4,'Full',5);
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
