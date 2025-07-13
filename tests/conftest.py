from pathlib import Path
import sys
import pytest

sys.path.append(str(Path(__file__).parent))
from utils import create_sample_db


@pytest.fixture(scope="session")
def seeded_db_path(tmp_path_factory):
    """Return a temporary database populated with sample data."""
    src_db = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "workout.db"
    db_path.write_bytes(src_db.read_bytes())
    create_sample_db(db_path)
    return db_path
