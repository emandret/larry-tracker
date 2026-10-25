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
