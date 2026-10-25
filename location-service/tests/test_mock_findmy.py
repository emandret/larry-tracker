from location_service.mock_findmy import MockAirTagState, MockFindMyClient


async def test_fetch_reports_returns_points_near_home():
    state = MockAirTagState(home_latitude=10.0, home_longitude=20.0, wander_radius_deg=0.01)
    client = MockFindMyClient(state=state, seed=42)

    points = await client.fetch_reports()

    # Each point is at most one wander step from the previous one (home, for the
    # first point), and a batch is at most 3 points -- so worst-case drift from
    # home is bounded by 3 steps.
    max_drift = 3 * state.wander_radius_deg

    assert points
    for p in points:
        assert abs(p.latitude - 10.0) < max_drift
        assert abs(p.longitude - 20.0) < max_drift


async def test_fetch_reports_is_deterministic_with_seed():
    client_a = MockFindMyClient(seed=1)
    client_b = MockFindMyClient(seed=1)

    points_a = await client_a.fetch_reports()
    points_b = await client_b.fetch_reports()

    assert [(p.latitude, p.longitude) for p in points_a] == [
        (p.latitude, p.longitude) for p in points_b
    ]
