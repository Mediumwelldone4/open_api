from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import (
    ConnectionConfig,
    ConnectionRecord,
    ConnectionTestResult,
    IngestionSummary,
    NumericSummary,
)
from app.repositories import InMemoryConnectionRepository
from app.routers import get_analysis_service, get_repository
from app.ai import AnalysisService
from app.settings import get_settings

pytestmark = pytest.mark.anyio("asyncio")


class FakeAnalysisService:
    async def analyze(self, *_, **__) -> str:  # noqa: ANN002, ANN003
        return "Review the trend based on the summarized data."


repository = InMemoryConnectionRepository()


def override_repository() -> InMemoryConnectionRepository:
    return repository


def override_analysis_service() -> FakeAnalysisService:
    return FakeAnalysisService()


app.dependency_overrides[get_repository] = override_repository
app.dependency_overrides[get_analysis_service] = override_analysis_service


@pytest.fixture
def anyio_backend():  # pragma: no cover - fix backend selection
    return "asyncio"


async def test_analysis_returns_answer_from_service() -> None:
    repository.clear()
    config = ConnectionConfig(
        portal_name="Portal",
        dataset_id="users",
        base_url="https://example.com",
        path="/users",
    )
    result = ConnectionTestResult(
        success=True,
        status_code=200,
        reason="OK",
        content_type="application/json",
        detected_format="json",
        record_count=1,
        schema_fields=["id"],
        preview="[]",
        preview_truncated=False,
        elapsed_ms=12,
    )
    record = repository.create(config, result)
    summary = IngestionSummary(
        record_count=12,
        schema_fields=["id", "value"],
        sample_records=[{"id": 1, "value": 10}, {"id": 2, "value": 20}],
        numeric_summary={
            "value": NumericSummary(mean=15.0, minimum=10.0, maximum=20.0),
        },
    )
    repository.set_ingestion_summary(record.id, summary, datetime.utcnow())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/connections/{record.id}/analysis",
            json={"question": "Summarize the trend for me"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert "trend" in response.json()["answer"].lower()


async def test_analysis_requires_question() -> None:
    repository.clear()
    config = ConnectionConfig(
        portal_name="Portal",
        dataset_id="users",
        base_url="https://example.com",
        path="/users",
    )
    result = ConnectionTestResult(
        success=True,
        status_code=200,
        reason="OK",
        content_type="application/json",
        detected_format="json",
        record_count=1,
        schema_fields=["id"],
        preview="[]",
        preview_truncated=False,
        elapsed_ms=12,
    )
    record = repository.create(config, result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"/connections/{record.id}/analysis", json={})

    assert response.status_code == status.HTTP_400_BAD_REQUEST


async def test_analysis_service_provides_stub_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("OPEN_DATA_OPENAI_API_KEY", "")
    get_settings.cache_clear()

    config = ConnectionConfig(
        portal_name="Seoul",
        dataset_id="traffic",
        base_url="https://example.com",
        path="/traffic",
    )
    summary = IngestionSummary(
        record_count=1200,
        schema_fields=["timestamp", "speed", "volume"],
        sample_records=[{"timestamp": "2024-01-01T00:00:00Z", "speed": 32, "volume": 10}],
        numeric_summary={
            "speed": NumericSummary(mean=40.0, minimum=12.0, maximum=88.0),
        },
    )
    record = ConnectionRecord(
        id=uuid4(),
        config=config,
        created_at=datetime.utcnow(),
        updated_at=None,
        last_test_result=None,
        last_ingested_at=datetime.utcnow(),
        last_ingestion_summary=summary,
    )

    service = AnalysisService()
    try:
        answer = await service.analyze(record, "Tell me the hour with the highest speed")
    finally:
        get_settings.cache_clear()

    assert "Offline mode" in answer
    assert "OPEN_DATA_OPENAI_API_KEY" in answer
