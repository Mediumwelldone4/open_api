from __future__ import annotations

import asyncio
import json
from typing import Any, List, Tuple
from urllib.parse import urljoin

import httpx
from xml.etree import ElementTree as ET

from .data_processing import DataProcessor
from .models import ConnectionConfig, IngestionSummary

MAX_PAGES = 5
MAX_RECORDS = 5000
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
BACKOFF_SECONDS = 0.75


class DataIngestionService:
    """Fetches datasets from configured portals and prepares processed snapshots."""

    def __init__(self, processor: DataProcessor | None = None) -> None:
        self._processor = processor or DataProcessor()

    async def ingest(self, config: ConnectionConfig) -> IngestionSummary:
        records = await self._collect_records(config)
        return self._processor.process(records)

    async def _collect_records(self, config: ConnectionConfig) -> List[dict[str, Any]]:
        params = {param.name: param.value for param in config.query_parameters}
        if config.api_key_name and config.api_key_value:
            params[config.api_key_name] = config.api_key_value.get_secret_value()

        target_url = urljoin(str(config.base_url), config.path)
        next_url: str | None = target_url
        collected: List[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            for page_number in range(MAX_PAGES):
                if next_url is None:
                    break

                attempt = 0
                response: httpx.Response
                while True:
                    response = await client.get(
                        next_url,
                        params=params if next_url == target_url and params else None,
                        headers={
                            "Accept": "application/json, application/xml;q=0.9, */*;q=0.8"
                        },
                    )
                    if response.status_code == httpx.codes.TOO_MANY_REQUESTS and attempt < MAX_RETRIES:
                        await asyncio.sleep(BACKOFF_SECONDS * (attempt + 1))
                        attempt += 1
                        continue
                    break

                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
                if "json" in content_type or config.data_format == "json":
                    payload = response.json()
                    page_records, next_pointer = self._extract_json_page(payload)
                elif "xml" in content_type or config.data_format == "xml":
                    page_records, next_pointer = self._extract_xml_page(response.text)
                else:
                    # Fall back to JSON parsing, raising if invalid.
                    try:
                        payload = response.json()
                        page_records, next_pointer = self._extract_json_page(payload)
                    except json.JSONDecodeError as exc:
                        raise RuntimeError("Unsupported content type for ingestion") from exc

                collected.extend(page_records)
                if len(collected) >= MAX_RECORDS:
                    collected = collected[:MAX_RECORDS]
                    break

                next_url, params = self._resolve_next_link(
                    next_pointer, response, config.base_url, params
                )

                if not next_url:
                    break

        return collected

    def _extract_json_page(self, payload: Any) -> Tuple[List[dict[str, Any]], Any]:
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
            return records, None

        if isinstance(payload, dict):
            if len(payload) == 1:
                inner_value = next(iter(payload.values()))
                inner_records, inner_next = self._extract_json_page(inner_value)
                if inner_records:
                    return inner_records, inner_next
            candidate_keys = ["results", "data", "items", "records"]
            for key in candidate_keys:
                value = payload.get(key)
                if isinstance(value, list):
                    records = [item for item in value if isinstance(item, dict)]
                    next_pointer = self._extract_next_pointer(payload)
                    return records, next_pointer
            if isinstance(payload.get("row"), list):
                row_value = payload.get("row")
                records = [item for item in row_value if isinstance(item, dict)]
                return records, None
            if all(isinstance(value, (str, int, float, bool, type(None))) for value in payload.values()):
                return [payload], None

        return [], None

    def _extract_next_pointer(self, payload: dict[str, Any]) -> Any:
        next_value = payload.get("next")
        if isinstance(next_value, (str, dict)):
            return next_value
        links = payload.get("links") or {}
        if isinstance(links, dict) and isinstance(links.get("next"), (str, dict)):
            return links["next"]
        return None

    def _extract_xml_page(self, text: str) -> Tuple[List[dict[str, Any]], Any]:
        root = ET.fromstring(text)
        records: List[dict[str, Any]] = []
        for element in root:
            record = {child.tag: (child.text or "").strip() for child in element}
            if record:
                records.append(record)
        if not records:
            records.append({root.tag: (root.text or "").strip()})
        return records, None

    def _resolve_next_link(
        self,
        next_pointer: Any,
        response: httpx.Response,
        base_url: httpx.URL | str,
        current_params: dict[str, Any],
    ) -> Tuple[str | None, dict[str, Any]]:
        if not next_pointer:
            link = response.links.get("next")
            if link and "url" in link:
                return link["url"], {}
            return None, current_params

        if isinstance(next_pointer, str):
            if next_pointer.startswith("http"):
                return next_pointer, {}
            return urljoin(str(base_url), next_pointer), {}

        if isinstance(next_pointer, dict):
            merged_params = {**current_params, **next_pointer}
            return urljoin(str(base_url), response.request.url.path), merged_params

        return None, current_params
