from __future__ import annotations

from backend import db_io
from backend import export_utils


def test_make_export_name(monkeypatch):
    class FixedDatetime(export_utils.datetime):  # type: ignore
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 8, 22, 14, 37, 5)

    monkeypatch.setattr(export_utils, "datetime", FixedDatetime)
    assert export_utils.make_export_name() == "workout_2025_08_22_14__37__05.db"


def test_export_database_auto_name(tmp_path, monkeypatch):
    class FixedDatetime(export_utils.datetime):  # type: ignore
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 8, 22, 14, 37, 5)

    monkeypatch.setattr(export_utils, "datetime", FixedDatetime)

    src = tmp_path / "source.db"
    src.write_text("data")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    exported = db_io.export_database(db_path=src, dest_dir=dest_dir)
    assert exported.name == "workout_2025_08_22_14__37__05.db"
    assert exported.exists()
    assert exported.parent == dest_dir

