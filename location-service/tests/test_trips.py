from datetime import datetime, timedelta, timezone

from location_service.trips import compute_trips, filter_quality, haversine_meters, trip_to_dict

HOME = (51.5, -0.1)


def make_point(lat: float, lon: float, ts: datetime, confidence: int = 3, accuracy: int = 10) -> dict:
    return {
        "timestamp": ts.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "confidence": confidence,
        "horizontal_accuracy": accuracy,
        "status": 0,
    }


def test_haversine_zero_distance_for_same_point():
    assert haversine_meters(51.5, -0.1, 51.5, -0.1) == 0


def test_haversine_known_distance_roughly_correct():
    # Roughly 111km per degree of latitude at the equator.
    distance = haversine_meters(0.0, 0.0, 1.0, 0.0)
    assert 110_000 < distance < 112_000


def test_compute_trips_splits_on_time_gap():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        make_point(51.5, -0.1, t0),
        make_point(51.501, -0.101, t0 + timedelta(minutes=5)),
        # big gap here
        make_point(51.6, -0.2, t0 + timedelta(hours=3)),
        make_point(51.601, -0.201, t0 + timedelta(hours=3, minutes=5)),
    ]

    trips = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)

    assert len(trips) == 2
    assert len(trips[0].points) == 2
    assert len(trips[1].points) == 2


def test_compute_trips_single_group_when_no_gap_exceeds_threshold():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [make_point(51.5, -0.1, t0 + timedelta(minutes=i * 10)) for i in range(5)]

    trips = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)

    assert len(trips) == 1
    assert len(trips[0].points) == 5


def test_compute_trips_marks_round_trip_when_ending_near_home():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        make_point(*HOME, t0),
        make_point(51.55, -0.2, t0 + timedelta(minutes=10)),  # far from home
        make_point(HOME[0] + 0.0001, HOME[1] + 0.0001, t0 + timedelta(minutes=20)),  # back near home
    ]

    trips = compute_trips(points, gap_minutes=45, home=HOME, home_radius_meters=75)

    assert len(trips) == 1
    assert trips[0].is_round_trip is True


def test_compute_trips_marks_one_way_when_not_returning_home():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [make_point(*HOME, t0), make_point(51.9, -0.5, t0 + timedelta(minutes=10))]

    trips = compute_trips(points, gap_minutes=45, home=HOME, home_radius_meters=75)

    assert trips[0].is_round_trip is False


def test_compute_trips_is_round_trip_none_without_home_configured():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [make_point(*HOME, t0)]

    trips = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)

    assert trips[0].is_round_trip is None


def test_compute_trips_empty_input():
    assert compute_trips([], gap_minutes=45, home=None, home_radius_meters=75) == []


def test_filter_quality_drops_low_confidence_and_low_accuracy_points():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        make_point(51.5, -0.1, t0, confidence=3, accuracy=10),
        make_point(51.5, -0.1, t0, confidence=0, accuracy=10),  # too low confidence
        make_point(51.5, -0.1, t0, confidence=3, accuracy=500),  # too inaccurate
    ]

    filtered = filter_quality(points, min_confidence=1, max_horizontal_accuracy_meters=100)

    assert len(filtered) == 1


def test_trip_to_dict_shape():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [make_point(*HOME, t0), make_point(*HOME, t0 + timedelta(minutes=30))]
    trip = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)[0]

    result = trip_to_dict(trip)

    assert result["point_count"] == 2
    assert result["duration_minutes"] == 30.0
    assert result["is_round_trip"] is None
    assert result["points"] == points
    assert result["distance_meters"] == 0.0
    assert result["average_speed_kmh"] == 0.0


def test_trip_to_dict_distance_and_speed():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        make_point(0.0, 0.0, t0),
        # ~111.2km north, 30 minutes later -- well within the 45min gap
        # threshold so this stays one trip (unrealistic cat speed, but this
        # is just checking the distance/speed arithmetic).
        make_point(1.0, 0.0, t0 + timedelta(minutes=30)),
    ]
    trip = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)[0]

    result = trip_to_dict(trip)

    assert 110_000 < result["distance_meters"] < 112_000
    assert 220 < result["average_speed_kmh"] < 224


def test_trip_to_dict_average_speed_none_for_zero_duration():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [make_point(*HOME, t0)]
    trip = compute_trips(points, gap_minutes=45, home=None, home_radius_meters=75)[0]

    result = trip_to_dict(trip)

    assert result["distance_meters"] == 0.0
    assert result["average_speed_kmh"] is None
