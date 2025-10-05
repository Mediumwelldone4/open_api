from uuid import UUID

import pytest

try:
    import respx
except ImportError:  # pragma: no cover
    respx = None

if respx is None:  # pragma: no cover
    pytest.skip("respx is not installed; skipping connection workflow tests", allow_module_level=True)
from fastapi import status
from httpx import AsyncClient, Response

from app.main import app
from app.routers import get_repository
from app.repositories import InMemoryConnectionRepository


test_repository = InMemoryConnectionRepository()


def override_repository() -> InMemoryConnectionRepository:
    return test_repository


app.dependency_overrides[get_repository] = override_repository


@pytest.mark.anyio
@respx.mock
async def test_connection_test_endpoint_returns_metadata_for_json_payload() -> None:
    test_repository.clear()
    api_route = respx.get("https://data.example.com/datasets/users").mock(
        return_value=Response(200, json=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}])
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/connections/test",
            json={
                "portal_name": "Example Portal",
                "dataset_id": "users",
                "base_url": "https://data.example.com",
                "path": "/datasets/users",
                "api_key_name": "api_key",
                "api_key_value": "secret",
                "query_parameters": [{"name": "limit", "value": "50"}],
            },
        )

    assert api_route.called
    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["success"] is True
    assert payload["status_code"] == 200
    assert payload["detected_format"] == "json"
    assert payload["record_count"] == 2
    assert "id" in payload["schema_fields"]
    assert payload["preview"].startswith("[")


@pytest.mark.anyio
@respx.mock
async def test_connection_test_endpoint_handles_xml_payload() -> None:
    test_repository.clear()
    xml_body = """
    <root>
        <item><id>1</id><name>Alice</name></item>
        <item><id>2</id><name>Bob</name></item>
    </root>
    """
    api_route = respx.get("https://data.example.com/datasets/xml").mock(
        return_value=Response(200, content=xml_body, headers={"content-type": "application/xml"})
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/connections/test",
            json={
                "portal_name": "Example Portal",
                "dataset_id": "xml-sample",
                "base_url": "https://data.example.com",
                "path": "/datasets/xml",
                "data_format": "auto",
                "query_parameters": [],
            },
        )

    assert api_route.called
    payload = response.json()
    assert payload["success"] is True
    assert payload["detected_format"] == "xml"
    assert payload["record_count"] == 2
    assert "root" in payload["schema_fields"]


@pytest.mark.anyio
@respx.mock
async def test_create_connection_persists_configuration_when_test_succeeds() -> None:
    test_repository.clear()
    respx.get("https://data.example.com/datasets/users").mock(
        return_value=Response(200, json=[{"id": 1, "name": "Alice"}])
    )

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        create_response = await client.post(
            "/connections",
            json={
                "portal_name": "Example Portal",
                "dataset_id": "users",
                "base_url": "https://data.example.com",
                "path": "/datasets/users",
                "query_parameters": [],
            },
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        created = create_response.json()
        assert UUID(created["id"])
        assert created["portal_name"] == "Example Portal"
        assert created["last_test_result"]["success"] is True
        assert created["last_test_result"]["record_count"] == 1
        assert created["last_ingested_at"] is None
        assert created["last_ingestion_summary"] is None

        list_response = await client.get("/connections")

    assert list_response.status_code == status.HTTP_200_OK
    listed = list_response.json()
    assert listed["count"] == 1
    assert listed["items"][0]["dataset_id"] == "users"
    assert listed["items"][0]["last_ingested_at"] is None

    detail_response = await client.get(f"/connections/{created['id']}")
    assert detail_response.status_code == status.HTTP_200_OK
    detail = detail_response.json()
    assert detail["id"] == created["id"]
    assert detail["portal_name"] == "Example Portal"
