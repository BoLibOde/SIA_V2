import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from fastapi.testclient import TestClient

from server.main import app


client = TestClient(app)


def test_health_endpoint_returns_ok_status_and_timestamp() -> None:
    response = client.get('/api/v1/health')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert 'timestamp' in data


def test_root_endpoint_returns_service_metadata() -> None:
    response = client.get('/')

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'sia-v2-api'
