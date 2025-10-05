from __future__ import annotations

import json
import time
from collections import Counter
from typing import Any
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, status
from xml.etree import ElementTree as ET

from .models import ConnectionConfig, ConnectionTestResult

PREVIEW_CHAR_LIMIT = 4000
REQUEST_TIMEOUT = 15.0


class ConnectionTester:
    """Encapsulates the logic for validating open-data API connections."""

    async def test(self, config: ConnectionConfig) -> ConnectionTestResult:
        start = time.perf_counter()
        params = {param.name: param.value for param in config.query_parameters}
        if config.api_key_name and config.api_key_value:
            params[config.api_key_name] = config.api_key_value.get_secret_value()

        target_url = urljoin(str(config.base_url), config.path)

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.get(
                    target_url,
                    params=params or None,
                    headers={
                        "Accept": "application/json, application/xml;q=0.9, */*;q=0.8"
                    },
                )
        except httpx.RequestError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return ConnectionTestResult(
                success=False,
                status_code=None,
                reason=None,
                content_type=None,
                detected_format="unknown",
                record_count=None,
                schema_fields=[],
                preview=None,
                preview_truncated=False,
                elapsed_ms=elapsed_ms,
                request_url=str(httpx.URL(target_url)),
                error=str(exc),
            )

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        content_type = response.headers.get("content-type", "").lower()
        raw_text = response.text
        preview_raw = raw_text[:PREVIEW_CHAR_LIMIT]
        preview_truncated = len(response.text) > PREVIEW_CHAR_LIMIT

        detected_format = self._detect_format(content_type, config.data_format)

        record_count: int | None = None
        schema_fields: list[str] = []

        if detected_format == "json":
            try:
                payload = response.json()
                record_count, schema_fields = self._summarize_json(payload)
                preview_payload = self._build_json_preview(payload)
                preview_text = json.dumps(preview_payload, ensure_ascii=False)
                preview_raw = preview_text[:PREVIEW_CHAR_LIMIT]
                preview_truncated = (
                    preview_truncated
                    or self._is_preview_truncated(payload)
                    or len(preview_text) > PREVIEW_CHAR_LIMIT
                )
            except (json.JSONDecodeError, ValueError):
                detected_format = "unknown"
        elif detected_format == "xml":
            try:
                record_count, schema_fields = self._summarize_xml(response.text)
            except ET.ParseError:
                detected_format = "unknown"

        return ConnectionTestResult(
            success=response.is_success,
            status_code=response.status_code,
            reason=response.reason_phrase,
            content_type=content_type or None,
            detected_format=detected_format,
            record_count=record_count,
            schema_fields=schema_fields,
            preview=preview_raw,
            preview_truncated=preview_truncated,
            elapsed_ms=elapsed_ms,
            request_url=str(httpx.URL(target_url).copy_with(params=params or None)),
            error=None if response.is_success else response.text[:512],
            raw_response=raw_text if response.is_success else response.text,
        )

    @staticmethod
    def _detect_format(content_type: str, preferred: str) -> str:
        if preferred in {"json", "xml"}:
            return preferred
        if "json" in content_type:
            return "json"
        if "xml" in content_type:
            return "xml"
        return "unknown"

    @staticmethod
    def _summarize_json(payload: Any) -> tuple[int | None, list[str]]:
        schema_counter: Counter[str] = Counter()
        record_count: int | None = None

        if isinstance(payload, list):
            record_count = len(payload)
            for item in payload[:50]:
                if isinstance(item, dict):
                    schema_counter.update(item.keys())
        elif isinstance(payload, dict):
            record_count = 1
            schema_counter.update(payload.keys())

        schema_fields = sorted(schema_counter.keys())[:50]
        return record_count, schema_fields

    @staticmethod
    def _build_json_preview(payload: Any) -> Any:
        if isinstance(payload, list):
            return payload[:5]
        if isinstance(payload, dict):
            return payload
        return payload

    @staticmethod
    def _is_preview_truncated(payload: Any) -> bool:
        if isinstance(payload, list):
            return len(payload) > 5
        return False

    @staticmethod
    def _summarize_xml(text: str) -> tuple[int | None, list[str]]:
        root = ET.fromstring(text)
        tag_counter: Counter[str] = Counter()

        def collect(element: ET.Element, depth: int = 0) -> None:
            if depth > 3:
                return
            tag_counter.update([element.tag])
            for child in element:
                collect(child, depth + 1)

        collect(root)
        # Count direct children as records when applicable
        record_count = len(list(root)) or 1
        schema_fields = sorted(tag_counter.keys())[:50]
        return record_count, schema_fields


async def ensure_success(result: ConnectionTestResult) -> ConnectionTestResult:
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error or result.reason or "Unable to validate dataset connection.",
        )
    return result
