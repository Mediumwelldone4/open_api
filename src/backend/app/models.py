from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, SecretStr


class QueryParameter(BaseModel):
    name: str = Field(..., description="Name of the query parameter.")
    value: str = Field(..., description="Value to send for the parameter.")


class ConnectionConfig(BaseModel):
    portal_name: str = Field(..., description="Human-friendly name of the open-data portal.")
    dataset_id: str = Field(..., description="Identifier for the dataset within the portal.")
    base_url: HttpUrl = Field(..., description="Base URL for the portal API.")
    path: str = Field(..., description="Endpoint path for the dataset.")
    api_key_name: str | None = Field(
        default=None,
        description="Query parameter name for the API key (if required).",
    )
    api_key_value: SecretStr | None = Field(
        default=None,
        description="API key value (stored securely; never returned in responses).",
    )
    data_format: Literal["auto", "json", "xml"] = Field(
        default="auto",
        description="Expected response format. Auto detects based on content-type.",
    )
    query_parameters: list[QueryParameter] = Field(
        default_factory=list,
        description="Additional static query parameters to include in requests.",
    )


class ConnectionTestResult(BaseModel):
    success: bool
    status_code: int | None = None
    reason: str | None = None
    content_type: str | None = None
    detected_format: Literal["json", "xml", "unknown"] = "unknown"
    record_count: int | None = None
    schema_fields: list[str] = Field(default_factory=list)
    preview: str | None = None
    preview_truncated: bool = False
    elapsed_ms: int = Field(..., description="Round-trip time for the test request.")
    request_url: HttpUrl | None = None
    error: str | None = None
    raw_response: str | None = None


class ConnectionRecord(BaseModel):
    id: UUID
    config: ConnectionConfig
    created_at: datetime
    updated_at: datetime | None = None
    last_test_result: ConnectionTestResult | None = None
    last_ingested_at: datetime | None = None
    last_ingestion_summary: IngestionSummary | None = None


class ConnectionResponse(BaseModel):
    id: UUID
    portal_name: str
    dataset_id: str
    base_url: HttpUrl
    path: str
    api_key_name: str | None
    data_format: Literal["auto", "json", "xml"]
    query_parameters: list[QueryParameter]
    created_at: datetime
    updated_at: datetime | None
    last_test_result: ConnectionTestResult | None
    last_ingested_at: datetime | None
    last_ingestion_summary: IngestionSummary | None

    @classmethod
    def from_record(cls, record: ConnectionRecord) -> "ConnectionResponse":
        return cls(
            id=record.id,
            portal_name=record.config.portal_name,
            dataset_id=record.config.dataset_id,
            base_url=record.config.base_url,
            path=record.config.path,
            api_key_name=record.config.api_key_name,
            data_format=record.config.data_format,
            query_parameters=record.config.query_parameters,
            created_at=record.created_at,
            updated_at=record.updated_at,
            last_test_result=record.last_test_result,
            last_ingested_at=record.last_ingested_at,
            last_ingestion_summary=record.last_ingestion_summary,
        )


class CreateConnectionResult(BaseModel):
    connection: ConnectionResponse


class CreateConnectionRequest(ConnectionConfig):
    pass


class ConnectionListResponse(BaseModel):
    items: list[ConnectionResponse]
    count: int

    @classmethod
    def from_records(cls, records: list[ConnectionRecord]) -> "ConnectionListResponse":
        return cls(
            items=[ConnectionResponse.from_record(record) for record in records],
            count=len(records),
        )


class NumericSummary(BaseModel):
    mean: Optional[float]
    minimum: Optional[float]
    maximum: Optional[float]


class IngestionSummary(BaseModel):
    record_count: Optional[int]
    schema_fields: list[str] = Field(default_factory=list)
    sample_records: list[Dict[str, Any]] = Field(default_factory=list)
    numeric_summary: Dict[str, NumericSummary] = Field(default_factory=dict)
    schema_details: list[Dict[str, Any]] = Field(default_factory=list)
    categorical_summary: Dict[str, list[Dict[str, Any]]] = Field(default_factory=dict)
    descriptive_stats: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    numeric_histograms: Dict[str, list[Dict[str, Any]]] = Field(default_factory=dict)


class IngestionJob(BaseModel):
    id: UUID
    connection_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: IngestionSummary | None = None
    message: str | None = None
    errors: list[str] = Field(default_factory=list)


class IngestionRequest(BaseModel):
    force_refresh: bool = False


class IngestionJobResponse(BaseModel):
    job_id: UUID
    connection_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    message: str | None
    errors: list[str]
    summary: IngestionSummary | None
