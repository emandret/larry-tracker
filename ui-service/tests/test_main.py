import respx
from fastapi.testclient import TestClient
from httpx import Response

from ui_service.main import app, settings

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_renders_map_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "leaflet" in response.text.lower()


@respx.mock
def test_api_path_proxies_location_service():
    respx.get(f"{settings.location_service_url}/locations").mock(
        return_value=Response(200, json=[{"latitude": 1.0, "longitude": 2.0, "timestamp": "t"}])
    )

    response = client.get("/api/path")

    assert response.status_code == 200
    assert response.json() == [{"latitude": 1.0, "longitude": 2.0, "timestamp": "t"}]


@respx.mock
def test_api_trips_proxies_location_service():
    body = {"home": None, "trips": [{"start": "t", "end": "t", "point_count": 1}]}
    respx.get(f"{settings.location_service_url}/trips").mock(return_value=Response(200, json=body))

    response = client.get("/api/trips")

    assert response.status_code == 200
    assert response.json() == body
