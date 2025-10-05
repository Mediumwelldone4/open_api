import pytest

try:
    import respx
except ImportError:  # pragma: no cover
    respx = None

if respx is None:  # pragma: no cover
    pytest.skip("respx is not installed; skipping ingestion tests", allow_module_level=True)
from fastapi import status
from httpx import Response

from app.models import (
    ConnectionConfig,
    ConnectionTestResult,
    QueryParameter,
)
from app.repositories import InMemoryConnectionRepository
from app.ingestion import DataIngestionService
from app.routers import _run_ingestion_job


@pytest.mark.anyio
@respx.mock
async def test_run_ingestion_job_collects_paginated_results() -> None:
    config = ConnectionConfig(
        portal_name="Example Portal",
        dataset_id="users",
        base_url="https://data.example.com",
        path="/datasets/users",
        query_parameters=[QueryParameter(name="pageSize", value="2")],
    )
    test_result = ConnectionTestResult(
        success=True,
        status_code=200,
        reason="OK",
        content_type="application/json",
        detected_format="json",
        record_count=2,
        schema_fields=["id"],
        preview="[]",
        preview_truncated=False,
        elapsed_ms=10,
    )
    repository = InMemoryConnectionRepository()
    connection = repository.create(config, test_result)

    first_page = respx.get("https://data.example.com/datasets/users").mock(
        return_value=Response(
            status.HTTP_200_OK,
            json={
                "results": [
                    {"id": 1, "value": "1"},
                    {"id": 2, "value": "2"},
                ],
                "next": "https://data.example.com/datasets/users?page=2",
            },
        )
    )
    second_page = respx.get("https://data.example.com/datasets/users?page=2").mock(
        return_value=Response(
            status.HTTP_200_OK,
            json={
                "results": [
                    {"id": 3, "value": "3"},
                    {"id": 4, "value": "4"},
                ],
                "next": None,
            },
        )
    )

    service = DataIngestionService()
    job = repository.create_job(connection.id)

    await _run_ingestion_job(job.id, repository, service)

    assert first_page.called
    assert second_page.called

    updated_job = repository.get_job(job.id)
    assert updated_job.status == "completed"
    assert updated_job.summary is not None
    assert updated_job.summary.record_count == 4
    assert "value" in updated_job.summary.schema_fields
    assert len(updated_job.summary.sample_records) > 0
    numeric_summary = updated_job.summary.numeric_summary
    assert "value" in numeric_summary
    assert numeric_summary["value"].maximum == 4

    refreshed_connection = repository.get(connection.id)
    assert refreshed_connection.last_ingested_at is not None
    assert refreshed_connection.last_ingestion_summary is not None


@pytest.mark.anyio
@respx.mock
async def test_run_ingestion_job_marks_failure_on_http_error() -> None:
    config = ConnectionConfig(
        portal_name="Example Portal",
        dataset_id="users",
        base_url="https://data.example.com",
        path="/datasets/users",
    )
    test_result = ConnectionTestResult(
        success=True,
        status_code=200,
        reason="OK",
        content_type="application/json",
        detected_format="json",
        record_count=1,
        schema_fields=["id"],
        preview="[]",
        preview_truncated=False,
        elapsed_ms=10,
    )
    repository = InMemoryConnectionRepository()
    connection = repository.create(config, test_result)

    respx.get("https://data.example.com/datasets/users").mock(return_value=Response(status.HTTP_500_INTERNAL_SERVER_ERROR))

    service = DataIngestionService()
    job = repository.create_job(connection.id)

    await _run_ingestion_job(job.id, repository, service)

    updated_job = repository.get_job(job.id)
    assert updated_job.status == "failed"
    assert updated_job.errors
    refreshed_connection = repository.get(connection.id)
    assert refreshed_connection.last_ingested_at is None
