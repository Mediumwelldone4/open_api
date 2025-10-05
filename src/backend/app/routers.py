from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from .models import (
    ConnectionConfig,
    ConnectionListResponse,
    ConnectionResponse,
    ConnectionTestResult,
    IngestionJob,
    IngestionJobResponse,
    IngestionRequest,
)
from .repositories import InMemoryConnectionRepository
from .services import ConnectionTester, ensure_success
from .ingestion import DataIngestionService
from .repository_factory import create_repository
from .settings import get_settings
from .ai import AnalysisService

router = APIRouter(prefix="/connections", tags=["connections"])


_repository_instance: InMemoryConnectionRepository | None = None


def get_repository() -> InMemoryConnectionRepository:
    global _repository_instance
    if _repository_instance is None:
        settings = get_settings()
        _repository_instance = create_repository(settings.database_url)
    return _repository_instance


def get_tester() -> ConnectionTester:
    if not hasattr(get_tester, "_tester"):
        get_tester._tester = ConnectionTester()  # type: ignore[attr-defined]
    return get_tester._tester  # type: ignore[attr-defined]


def get_ingestion_service() -> DataIngestionService:
    if not hasattr(get_ingestion_service, "_service"):
        get_ingestion_service._service = DataIngestionService()  # type: ignore[attr-defined]
    return get_ingestion_service._service  # type: ignore[attr-defined]


def get_analysis_service() -> AnalysisService:
    return AnalysisService()


def _job_to_response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        job_id=job.id,
        connection_id=job.connection_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        message=job.message,
        errors=job.errors,
        summary=job.summary,
    )


@router.post("/test", response_model=ConnectionTestResult)
async def test_connection(
    payload: ConnectionConfig,
    tester: ConnectionTester = Depends(get_tester),
) -> ConnectionTestResult:
    return await tester.test(payload)


@router.post("", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    payload: ConnectionConfig,
    tester: ConnectionTester = Depends(get_tester),
    repository: InMemoryConnectionRepository = Depends(get_repository),
) -> ConnectionResponse:
    test_result = await tester.test(payload)
    await ensure_success(test_result)
    record = repository.create(payload, test_result)
    return ConnectionResponse.from_record(record)


@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    repository: InMemoryConnectionRepository = Depends(get_repository),
) -> ConnectionListResponse:
    records = list(repository.list())
    return ConnectionListResponse.from_records(records)


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: UUID,
    repository: InMemoryConnectionRepository = Depends(get_repository),
) -> ConnectionResponse:
    try:
        record = repository.get(connection_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found") from exc
    return ConnectionResponse.from_record(record)


@router.post(
    "/{connection_id}/analysis",
    summary="Generate AI insights for a dataset",
)
async def analyze_connection(
    connection_id: UUID,
    payload: dict[str, str],
    repository: InMemoryConnectionRepository = Depends(get_repository),
    service: AnalysisService = Depends(get_analysis_service),
) -> dict[str, str]:
    question = payload.get("question")
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required.",
        )

    try:
        record = repository.get(connection_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found") from exc

    answer = await service.analyze(record, question)
    return {"answer": answer}


@router.post(
    "/{connection_id}/ingest",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ingestion(
    connection_id: UUID,
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    repository: InMemoryConnectionRepository = Depends(get_repository),
    service: DataIngestionService = Depends(get_ingestion_service),
) -> IngestionJobResponse:
    try:
        repository.get(connection_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found") from exc

    active_jobs = [
        job for job in repository.list_jobs_for_connection(connection_id) if job.status in {"pending", "running"}
    ]
    if active_jobs and not request.force_refresh:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An ingestion job is already in progress for this connection.",
        )

    job = repository.create_job(connection_id)
    background_tasks.add_task(_run_ingestion_job, job.id, repository, service)
    return _job_to_response(job)


@router.get(
    "/{connection_id}/ingest/{job_id}",
    response_model=IngestionJobResponse,
)
async def get_ingestion_job(
    connection_id: UUID,
    job_id: UUID,
    repository: InMemoryConnectionRepository = Depends(get_repository),
) -> IngestionJobResponse:
    try:
        job = repository.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found") from exc

    if job.connection_id != connection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not associated with connection")

    return _job_to_response(job)


async def _run_ingestion_job(
    job_id: UUID,
    repository: InMemoryConnectionRepository,
    service: DataIngestionService,
) -> None:
    started_at = datetime.utcnow()
    job = repository.update_job(job_id, status="running", started_at=started_at)
    connection = repository.get(job.connection_id)

    try:
        summary = await service.ingest(connection.config)
    except Exception as exc:  # noqa: BLE001 broad exception for job capture
        repository.update_job(
            job_id,
            status="failed",
            finished_at=datetime.utcnow(),
            message=str(exc),
            errors=[str(exc)],
        )
        return

    finished_at = datetime.utcnow()
    repository.update_job(
        job_id,
        status="completed",
        finished_at=finished_at,
        summary=summary,
        message="Ingestion finished successfully",
    )
    repository.set_ingestion_summary(connection.id, summary, finished_at)
