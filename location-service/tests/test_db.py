from datetime import datetime, timezone

from location_service import db
from location_service.findmy_client import LocationPoint


def make_point(lat: float, lon: float, ts: datetime) -> LocationPoint:
    return LocationPoint(
        timestamp=ts,
        latitude=lat,
        longitude=lon,
        confidence=3,
        horizontal_accuracy=10,
        status=0,
    )


def test_insert_and_get_points(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    inserted = db.insert_points(db_path, [make_point(1.0, 2.0, t1), make_point(1.1, 2.1, t2)])

    assert inserted == 2
    points = db.get_points(db_path)
    assert [p["latitude"] for p in points] == [1.0, 1.1]


def test_insert_points_deduplicates(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    point = make_point(1.0, 2.0, t1)

    assert db.insert_points(db_path, [point]) == 1
    assert db.insert_points(db_path, [point]) == 0
    assert len(db.get_points(db_path)) == 1


def test_get_latest_point(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)

    assert db.get_latest_point(db_path) is None

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)
    db.insert_points(db_path, [make_point(1.0, 2.0, t1), make_point(1.1, 2.1, t2)])

    latest = db.get_latest_point(db_path)
    assert latest["latitude"] == 1.1


def test_get_point_by_id(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)

    assert db.get_point(db_path, 1) is None

    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    [point] = db.get_points(db_path)

    assert db.get_point(db_path, point["id"]) == point


def test_update_point_changes_whitelisted_fields(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    [point] = db.get_points(db_path)

    changed = db.update_point(db_path, point["id"], {"latitude": 9.9, "longitude": 8.8})

    assert changed is True
    updated = db.get_point(db_path, point["id"])
    assert updated["latitude"] == 9.9
    assert updated["longitude"] == 8.8


def test_update_point_ignores_unknown_fields(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    [point] = db.get_points(db_path)

    # "id" is not in the update whitelist -- attempting to change it should
    # be silently dropped rather than touching the primary key.
    changed = db.update_point(db_path, point["id"], {"id": 999})

    assert changed is False
    assert db.get_point(db_path, point["id"])["id"] == point["id"]


def test_update_point_returns_false_for_missing_point(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)

    assert db.update_point(db_path, 999, {"latitude": 1.0}) is False


def test_delete_point(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    [point] = db.get_points(db_path)

    assert db.delete_point(db_path, point["id"]) is True
    assert db.get_point(db_path, point["id"]) is None
    assert db.delete_point(db_path, point["id"]) is False


def test_delete_points_removes_all_given_ids(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(
        db_path,
        [
            make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc)),
            make_point(3.0, 4.0, datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)),
            make_point(5.0, 6.0, datetime(2026, 1, 1, 0, 10, tzinfo=timezone.utc)),
        ],
    )
    points = db.get_points(db_path)
    ids_to_delete = [points[0]["id"], points[1]["id"]]

    deleted = db.delete_points(db_path, ids_to_delete)

    assert deleted == 2
    remaining = db.get_points(db_path)
    assert [p["id"] for p in remaining] == [points[2]["id"]]


def test_delete_points_empty_list_deletes_nothing(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])

    assert db.delete_points(db_path, []) == 0
    assert len(db.get_points(db_path)) == 1


def test_delete_points_ignores_unknown_ids(tmp_path):
    db_path = str(tmp_path / "larry.db")
    db.init_db(db_path)
    db.insert_points(db_path, [make_point(1.0, 2.0, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    [point] = db.get_points(db_path)

    deleted = db.delete_points(db_path, [point["id"], 999])

    assert deleted == 1
    assert db.get_points(db_path) == []
