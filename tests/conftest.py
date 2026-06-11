import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope='session')
def client() -> TestClient:
    os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

    from server.main import app

    with TestClient(app) as test_client:
        yield test_client
