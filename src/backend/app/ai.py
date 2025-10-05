from __future__ import annotations

import asyncio
from textwrap import dedent

from fastapi import HTTPException, status
from openai import OpenAI

from .models import ConnectionRecord, IngestionSummary
from .settings import get_settings

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
        if settings.openai_api_key is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI API key is not configured. Set OPEN_DATA_OPENAI_API_KEY.",
            )
        self._client = OpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def analyze(self, connection: ConnectionRecord, question: str) -> str:
        if not connection.last_ingestion_summary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ingestion summary available. Run data ingestion first.",
            )

        payload = self._build_prompt(connection.last_ingestion_summary, question)
        return await asyncio.to_thread(self._run_completion, payload)

    def _run_completion(self, prompt: str) -> str:
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
            - Schema details:\n{chr(10).join(schema_lines) if schema_lines else "  (제공되지 않음)"}
            - Numeric summary: {numeric}
            - Categorical summary (top values): {categorical}
            - Sample records: {sample}

            Question: {question}
            Provide concise, factual insights and suggest next steps if applicable.
            """
        ).strip()
