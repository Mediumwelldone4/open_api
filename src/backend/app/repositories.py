from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable
from uuid import UUID, uuid4

from pydantic import SecretStr

from .models import (
    ConnectionConfig,
    ConnectionRecord,
    ConnectionTestResult,
    IngestionJob,
    IngestionSummary,
    QueryParameter,
)


class InMemoryConnectionRepository:
    """Simple in-memory repository for dataset connections."""

    def __init__(self) -> None:
        self._records: Dict[UUID, ConnectionRecord] = {}
        self._jobs: Dict[UUID, IngestionJob] = {}

    def create(
        self, config: ConnectionConfig, last_test_result: ConnectionTestResult
    ) -> ConnectionRecord:
        record_id = uuid4()
        record = ConnectionRecord(
            id=record_id,
            config=config,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_test_result=last_test_result,
        )
        self._records[record_id] = record
        return record

    def list(self) -> Iterable[ConnectionRecord]:
        return list(self._records.values())

    def get(self, record_id: UUID) -> ConnectionRecord:
        return self._records[record_id]

    def create_job(self, connection_id: UUID) -> IngestionJob:
        job = IngestionJob(
            id=uuid4(),
            connection_id=connection_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self._jobs[job.id] = job
        return job

    def update_job(self, job_id: UUID, **updates) -> IngestionJob:
        job = self._jobs[job_id]
        updated = job.model_copy(update=updates)
        self._jobs[job_id] = updated
        return updated

    def get_job(self, job_id: UUID) -> IngestionJob:
        return self._jobs[job_id]

    def list_jobs_for_connection(self, connection_id: UUID) -> Iterable[IngestionJob]:
        return [job for job in self._jobs.values() if job.connection_id == connection_id]

    def set_ingestion_summary(
        self, connection_id: UUID, summary: IngestionSummary, timestamp: datetime
    ) -> ConnectionRecord:
        record = self._records[connection_id]
        updated = record.model_copy(
            update={
                "last_ingested_at": timestamp,
                "last_ingestion_summary": summary,
                "updated_at": timestamp,
            }
        )
        self._records[connection_id] = updated
        return updated

    def clear(self) -> None:
        self._records.clear()
        self._jobs.clear()


class SQLiteConnectionRepository(InMemoryConnectionRepository):
    """SQLite-backed repository for connections and ingestion jobs."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        path: Path | None
        if db_path is None:
            path = Path("data") / "open_data_insight.db"
        elif isinstance(db_path, Path):
            path = db_path
        elif db_path == ":memory:":
            path = None
        else:
            path = Path(db_path)

        self._db_path = path
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            db_target = path
        else:
            db_target = ":memory:"

        self._connection = sqlite3.connect(db_target, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self._connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY,
                portal_name TEXT NOT NULL,
                dataset_id TEXT NOT NULL,
                base_url TEXT NOT NULL,
                path TEXT NOT NULL,
                api_key_name TEXT,
                api_key_value TEXT,
                data_format TEXT NOT NULL,
                query_parameters TEXT NOT NULL,
                config_json TEXT NOT NULL,
                last_test_result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                last_ingested_at TEXT,
                last_ingestion_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id TEXT PRIMARY KEY,
                connection_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                message TEXT,
                errors TEXT,
                summary TEXT,
                FOREIGN KEY(connection_id) REFERENCES connections(id)
            );
            """
        )
        self._connection.commit()

    def _serialize_config(self, config: ConnectionConfig) -> str:
        return json.dumps({
            "portal_name": config.portal_name,
            "dataset_id": config.dataset_id,
            "base_url": str(config.base_url),
            "path": config.path,
            "api_key_name": config.api_key_name,
            "data_format": config.data_format,
            "query_parameters": [param.model_dump() for param in config.query_parameters],
        })

    def _serialize_test_result(self, result: ConnectionTestResult | None) -> str | None:
        if result is None:
            return None
        return result.model_dump_json()

    def _deserialize_test_result(self, data: str | None) -> ConnectionTestResult | None:
        if not data:
            return None
        return ConnectionTestResult.model_validate_json(data)

    def _serialize_summary(self, summary: IngestionSummary | None) -> str | None:
        if summary is None:
            return None
        return summary.model_dump_json()

    def _deserialize_summary(self, data: str | None) -> IngestionSummary | None:
        if not data:
            return None
        return IngestionSummary.model_validate_json(data)

    def _row_to_connection_record(self, row: sqlite3.Row) -> ConnectionRecord:
        config_payload = json.loads(row["config_json"])
        api_key_value = row["api_key_value"]
        config = ConnectionConfig(
            portal_name=config_payload["portal_name"],
            dataset_id=config_payload["dataset_id"],
            base_url=config_payload["base_url"],
            path=config_payload["path"],
            api_key_name=config_payload.get("api_key_name"),
            api_key_value=SecretStr(api_key_value) if api_key_value else None,
            data_format=config_payload["data_format"],
            query_parameters=[QueryParameter(**param) for param in config_payload["query_parameters"]],
        )
        test_result = self._deserialize_test_result(row["last_test_result"])
        return ConnectionRecord(
            id=UUID(row["id"]),
            config=config,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            last_test_result=test_result,
            last_ingested_at=datetime.fromisoformat(row["last_ingested_at"]) if row["last_ingested_at"] else None,
            last_ingestion_summary=self._deserialize_summary(row["last_ingestion_summary"]),
        )

    def create(
        self, config: ConnectionConfig, last_test_result: ConnectionTestResult
    ) -> ConnectionRecord:
        record_id = uuid4()
        created_at = datetime.utcnow()
        config_payload = self._serialize_config(config)
        test_result_payload = self._serialize_test_result(last_test_result)

        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO connections (
                id, portal_name, dataset_id, base_url, path, api_key_name, api_key_value,
                data_format, query_parameters, config_json, last_test_result,
                created_at, updated_at, last_ingested_at, last_ingestion_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(record_id),
                config.portal_name,
                config.dataset_id,
                str(config.base_url),
                config.path,
                config.api_key_name,
                config.api_key_value.get_secret_value() if config.api_key_value else None,
                config.data_format,
                json.dumps([param.model_dump() for param in config.query_parameters]),
                config_payload,
                test_result_payload,
                created_at.isoformat(),
                created_at.isoformat(),
                None,
                None,
            ),
        )
        self._connection.commit()

        return ConnectionRecord(
            id=record_id,
            config=config,
            created_at=created_at,
            updated_at=created_at,
            last_test_result=last_test_result,
            last_ingested_at=None,
            last_ingestion_summary=None,
        )

    def list(self) -> Iterable[ConnectionRecord]:
        cursor = self._connection.cursor()
        rows = cursor.execute("SELECT * FROM connections").fetchall()
        return [self._row_to_connection_record(row) for row in rows]

    def get(self, record_id: UUID) -> ConnectionRecord:
        cursor = self._connection.cursor()
        row = cursor.execute(
            "SELECT * FROM connections WHERE id = ?", (str(record_id),)
        ).fetchone()
        if row is None:
            raise KeyError(f"Connection {record_id} not found")
        return self._row_to_connection_record(row)

    def create_job(self, connection_id: UUID) -> IngestionJob:
        job = IngestionJob(
            id=uuid4(),
            connection_id=connection_id,
            status="pending",
            created_at=datetime.utcnow(),
        )
        cursor = self._connection.cursor()
        cursor.execute(
            """
            INSERT INTO ingestion_jobs (
                id, connection_id, status, created_at, started_at, finished_at,
                message, errors, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job.id),
                str(job.connection_id),
                job.status,
                job.created_at.isoformat(),
                None,
                None,
                None,
                json.dumps([]),
                None,
            ),
        )
        self._connection.commit()
        return job

    def update_job(self, job_id: UUID, **updates) -> IngestionJob:
        job = self.get_job(job_id)
        updated = job.model_copy(update=updates)
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE ingestion_jobs
            SET status = ?, started_at = ?, finished_at = ?, message = ?, errors = ?, summary = ?
            WHERE id = ?
            """,
            (
                updated.status,
                updated.started_at.isoformat() if updated.started_at else None,
                updated.finished_at.isoformat() if updated.finished_at else None,
                updated.message,
                json.dumps(updated.errors),
                self._serialize_summary(updated.summary),
                str(job_id),
            ),
        )
        self._connection.commit()
        return updated

    def get_job(self, job_id: UUID) -> IngestionJob:
        cursor = self._connection.cursor()
        row = cursor.execute(
            "SELECT * FROM ingestion_jobs WHERE id = ?", (str(job_id),)
        ).fetchone()
        if row is None:
            raise KeyError(f"Job {job_id} not found")
        return IngestionJob(
            id=UUID(row["id"]),
            connection_id=UUID(row["connection_id"]),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            message=row["message"],
            errors=json.loads(row["errors"]) if row["errors"] else [],
            summary=self._deserialize_summary(row["summary"]),
        )

    def list_jobs_for_connection(self, connection_id: UUID) -> Iterable[IngestionJob]:
        cursor = self._connection.cursor()
        rows = cursor.execute(
            "SELECT * FROM ingestion_jobs WHERE connection_id = ?",
            (str(connection_id),),
        ).fetchall()
        return [
            IngestionJob(
                id=UUID(row["id"]),
                connection_id=UUID(row["connection_id"]),
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
                message=row["message"],
                errors=json.loads(row["errors"]) if row["errors"] else [],
                summary=self._deserialize_summary(row["summary"]),
            )
            for row in rows
        ]

    def set_ingestion_summary(
        self, connection_id: UUID, summary: IngestionSummary, timestamp: datetime
    ) -> ConnectionRecord:
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE connections
            SET last_ingested_at = ?, last_ingestion_summary = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                timestamp.isoformat(),
                self._serialize_summary(summary),
                timestamp.isoformat(),
                str(connection_id),
            ),
        )
        self._connection.commit()
        return self.get(connection_id)

    def clear(self) -> None:
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM ingestion_jobs")
        cursor.execute("DELETE FROM connections")
        self._connection.commit()
