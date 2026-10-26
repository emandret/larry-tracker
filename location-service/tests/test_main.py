import os
from datetime import datetime, timezone

os.environ.setdefault("FINDMY_MODE", "mock")
os.environ.setdefault("POLL_INTERVAL_SECONDS", "3600")  # keep the background poller quiet in tests

import pytest
from fastapi.testclient import TestClient

from location_service import db
from location_service.findmy_client import LocationPoint
from location_service.main import app, settings

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path):
    # `settings` is a frozen dataclass -- object.__setattr__ bypasses that,
    # same trick the stdlib itself uses for post-init mutation.
    object.__setattr__(settings, "db_path", str(tmp_path / "test.db"))
    db.init_db(settings.db_path)


def insert_test_point(lat: float = 1.0, lon: float = 2.0) -> dict:
    point = LocationPoint(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        latitude=lat,
        longitude=lon,
        confidence=3,
        horizontal_accuracy=10,
        status=0,
    )
    db.insert_points(settings.db_path, [point])
    matches = [p for p in db.get_points(settings.db_path) if p["latitude"] == lat and p["longitude"] == lon]
    return matches[-1]


def test_update_location_changes_fields():
    point = insert_test_point()

    response = client.patch(f"/locations/{point['id']}", json={"latitude": 9.9})

    assert response.status_code == 200
    assert response.json()["latitude"] == 9.9


def test_update_location_404_for_missing_point():
    response = client.patch("/locations/999", json={"latitude": 1.0})
    assert response.status_code == 404


def test_update_location_400_for_empty_body():
    point = insert_test_point()

    response = client.patch(f"/locations/{point['id']}", json={})

    assert response.status_code == 400


def test_update_location_409_when_result_collides_with_another_point():
    insert_test_point(lat=1.0, lon=2.0)
    other = insert_test_point(lat=3.0, lon=4.0)

    response = client.patch(f"/locations/{other['id']}", json={"latitude": 1.0, "longitude": 2.0})

    assert response.status_code == 409


def test_delete_location():
    point = insert_test_point()

    response = client.delete(f"/locations/{point['id']}")

    assert response.status_code == 204
    assert db.get_point(settings.db_path, point["id"]) is None


def test_delete_location_404_for_missing_point():
    response = client.delete("/locations/999")

    assert response.status_code == 404


def test_websocket_broadcasts_on_update():
    point = insert_test_point()

    with client.websocket_connect("/ws") as websocket:
        response = client.patch(f"/locations/{point['id']}", json={"latitude": 5.0})
        assert response.status_code == 200

        message = websocket.receive_json()
        assert message == {"type": "locations_updated"}


def test_websocket_broadcasts_on_delete():
    point = insert_test_point()

    with client.websocket_connect("/ws") as websocket:
        response = client.delete(f"/locations/{point['id']}")
        assert response.status_code == 204

        message = websocket.receive_json()
        assert message == {"type": "locations_updated"}


def test_bulk_delete_locations_removes_all_given_ids():
    a = insert_test_point(lat=1.0, lon=2.0)
    b = insert_test_point(lat=3.0, lon=4.0)
    kept = insert_test_point(lat=5.0, lon=6.0)

    response = client.post("/locations/bulk-delete", json={"ids": [a["id"], b["id"]]})

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}
    remaining = db.get_points(settings.db_path)
    assert [p["id"] for p in remaining] == [kept["id"]]


def test_bulk_delete_locations_empty_ids_is_a_noop():
    insert_test_point()

    response = client.post("/locations/bulk-delete", json={"ids": []})

    assert response.status_code == 200
    assert response.json() == {"deleted": 0}
    assert len(db.get_points(settings.db_path)) == 1


def test_websocket_broadcasts_on_bulk_delete():
    point = insert_test_point()

    with client.websocket_connect("/ws") as websocket:
        response = client.post("/locations/bulk-delete", json={"ids": [point["id"]]})
        assert response.status_code == 200

        message = websocket.receive_json()
        assert message == {"type": "locations_updated"}


