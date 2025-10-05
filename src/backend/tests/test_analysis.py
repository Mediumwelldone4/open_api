from datetime import datetime

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import (
    ConnectionConfig,
    ConnectionTestResult,
    IngestionSummary,
    NumericSummary,
)
from app.repositories import InMemoryConnectionRepository
from app.routers import get_analysis_service, get_repository

pytestmark = pytest.mark.anyio("asyncio")


class FakeAnalysisService:
    async def analyze(self, *_, **__) -> str:  # noqa: ANN002, ANN003
        return "요약된 데이터를 기반으로 추세를 검토하세요."


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
            json={"question": "값의 추세를 요약해줘"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert "추세" in response.json()["answer"]


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
