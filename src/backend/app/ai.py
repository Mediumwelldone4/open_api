from __future__ import annotations

import asyncio
import logging
from textwrap import dedent

from fastapi import HTTPException, status
from openai import OpenAI

from .models import ConnectionRecord, IngestionSummary
from .settings import get_settings


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = dedent(
    """
    You are an assistant helping analysts interpret datasets fetched from public APIs.
    Respond in Korean when the user writes in Korean, otherwise respond in English.
    Base your answers only on the dataset summary provided. If information is missing,
    explain what additional data would be needed.
    """
)


class AnalysisService:
    """Wraps OpenAI Responses API to generate insights from dataset summaries."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client: OpenAI | None = None
        self._use_stub = False

        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""

        if api_key.strip():
            self._client = OpenAI(api_key=api_key)
        else:
            self._use_stub = True
            logger.warning(
                "OPEN_DATA_OPENAI_API_KEY is not configured; falling back to offline insight stubs.",
            )

    async def analyze(self, connection: ConnectionRecord, question: str) -> str:
        if not connection.last_ingestion_summary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ingestion summary available. Run data ingestion first.",
            )

        if self._use_stub:
            return self._generate_stub_response(connection, question)

        payload = self._build_prompt(connection.last_ingestion_summary, question)
        return await asyncio.to_thread(self._run_completion, payload)

    def _run_completion(self, prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("AnalysisService run called without OpenAI client")

        try:
            response = self._client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.output[0].content[0]
            return getattr(content, "text", "")
        except AttributeError:
            completion = self._client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content or ""

    def _generate_stub_response(self, connection: ConnectionRecord, question: str) -> str:
        summary = connection.last_ingestion_summary
        assert summary is not None  # enforce upstream check

        bullet_points: list[str] = []
        if summary.record_count is not None:
            bullet_points.append(f"- Approximate records: {summary.record_count}")

        if summary.schema_fields:
            fields_preview = ", ".join(summary.schema_fields[:5])
            if len(summary.schema_fields) > 5:
                fields_preview += " and more"
            bullet_points.append(f"- Key fields: {fields_preview}")

        if summary.numeric_summary:
            metrics = ", ".join(sorted(summary.numeric_summary.keys())[:5])
            bullet_points.append(f"- Numeric metrics: {metrics}")

        bullet_text = "\n".join(bullet_points) if bullet_points else "- Not enough summary information available."

        return (
            "[Offline mode] OpenAI API key is missing. Showing a fallback summary.\n"
            f"Dataset: {connection.config.portal_name} / {connection.config.dataset_id}\n"
            f"Question: {question.strip()}\n"
            f"Summary highlights:\n{bullet_text}\n"
            "Set the OPEN_DATA_OPENAI_API_KEY environment variable to enable AI-powered analysis."
        )

    def _build_prompt(self, summary: IngestionSummary, question: str) -> str:
        schema_lines = []
        for detail in summary.schema_details[:20]:
            column = detail.get("column")
            dtype = detail.get("dtype")
            non_null = detail.get("non_null")
            schema_lines.append(f"- {column} ({dtype}), non-null: {non_null}")

        record_count = summary.record_count or "Unknown"
        numeric = {
            field: stats.model_dump()
            for field, stats in summary.numeric_summary.items()
        }
        categorical = summary.categorical_summary
        sample = summary.sample_records[:5]

        return dedent(
            f"""
            Dataset overview:
            - Record count: {record_count}
            - Schema details:\n{chr(10).join(schema_lines) if schema_lines else "  (not provided)"}
            - Numeric summary: {numeric}
            - Categorical summary (top values): {categorical}
            - Sample records: {sample}

            Question: {question}
            Provide concise, factual insights and suggest next steps if applicable.
            """
        ).strip()
