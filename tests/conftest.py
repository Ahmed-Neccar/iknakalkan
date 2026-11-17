import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import init_db  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    """Her test için geçici, temiz bir veritabanı."""
    connection = init_db(tmp_path / "test.db")
    yield connection
    connection.close()
