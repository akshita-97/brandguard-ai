import os
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["DATABASE_PATH"] = os.path.join(_tmp, "test.db")
os.environ["AI_API_KEY"] = ""

import pytest
from FlaskWebProject1.db import init_db

init_db()


@pytest.fixture(autouse=True)
def _fresh_db():
    from FlaskWebProject1.db import get_connection
    conn = get_connection()
    for t in ("findings", "reviews", "brand_facts", "brand_rules", "brand_profiles"):
        conn.execute(f"DELETE FROM {t}")
    conn.commit()
    conn.close()
    init_db()
    yield
