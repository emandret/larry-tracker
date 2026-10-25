from location_service.config import Settings
from location_service.findmy_client import build_client
from location_service.mock_findmy import MockFindMyClient

BASE_KWARGS = dict(
    findmy_mode="mock",
    db_path=":memory:",
    poll_interval_seconds=300,
    account_store_path="/data/account.json",
    anisette_libs_path="/data/ani_libs.bin",
    anisette_server_url=None,
    airtag_key_b64=None,
    trip_gap_minutes=45,
    home_radius_meters=75,
    min_confidence=1,
    max_horizontal_accuracy_meters=100,
)


async def test_mock_client_wanders_around_configured_home():
    settings = Settings(**BASE_KWARGS, home_latitude=10.0, home_longitude=20.0)

    client = build_client(settings)
    assert isinstance(client, MockFindMyClient)

    points = await client.fetch_reports()

    # Should wander around the *configured* home, not some unrelated default.
    for p in points:
        assert abs(p.latitude - 10.0) < 0.02
        assert abs(p.longitude - 20.0) < 0.02


async def test_mock_client_falls_back_to_default_home_when_unconfigured():
    settings = Settings(**BASE_KWARGS, home_latitude=None, home_longitude=None)

    client = build_client(settings)
    points = await client.fetch_reports()

    assert points  # just needs to not blow up and produce something
