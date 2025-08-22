# Database Backup Guide

The project uses two different backup locations:

- `backups/` – manual snapshots created by developers during migrations or other maintenance tasks.
- `data/backup/` – automatic backup used by the app at runtime. It stores a single copy of `workout.db` that is kept up to date.

## Automatic Backup Workflow

A fresh backup is written to `data/backup/workout.db` after each of the following actions:

- saving a metric definition or override
- saving a user exercise
- saving a preset
- completing a workout session

Each backup overwrites the previous one; only the most recent copy is retained. The file is written via a temporary file and atomic rename to avoid corrupting both the live database and the backup.

## Automatic Restore

On startup the app verifies `data/workout.db` with `PRAGMA integrity_check`. If the database is missing or corrupt, the app deletes it and restores the last backup from `data/backup/workout.db`.

These mechanisms ensure a fallback is always available without keeping a long history of backups.
