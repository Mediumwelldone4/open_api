from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .models import IngestionSummary, NumericSummary


class DataProcessor:
    """Transforms raw records into DataFrame-powered summaries."""

    SAMPLE_LIMIT = 50
    TOP_CATEGORIES = 5

    def process(self, records: List[dict[str, Any]]) -> IngestionSummary:
        if not records:
            return IngestionSummary(record_count=0)

        df = pd.DataFrame(records)
        if df.empty:
            return IngestionSummary(record_count=0)

        schema_details = self._build_schema(df)
        schema_fields = [detail["column"] for detail in schema_details]
        sample_records = self._build_samples(df)
        numeric_summary = self._build_numeric_summary(df)
        categorical_summary = self._build_categorical_summary(df)
        descriptive_stats = self._build_describe(df)
        numeric_histograms = self._build_histograms(df)

        return IngestionSummary(
            record_count=int(len(df)),
            schema_fields=schema_fields,
            schema_details=schema_details,
            sample_records=sample_records,
            numeric_summary=numeric_summary,
            categorical_summary=categorical_summary,
            descriptive_stats=descriptive_stats,
            numeric_histograms=numeric_histograms,
        )

    def _build_schema(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        schema: List[Dict[str, Any]] = []
        for column in df.columns:
            non_null = int(df[column].count())
            schema.append(
                {
                    "column": column,
                    "dtype": str(df[column].dtype),
                    "non_null": non_null,
                    "null_count": int(len(df) - non_null),
                }
            )
        return schema

    def _build_samples(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        sample_df = df.head(self.SAMPLE_LIMIT)
        sample_df = sample_df.replace({pd.NA: None}).fillna("")
        return sample_df.to_dict(orient="records")

    def _build_numeric_summary(self, df: pd.DataFrame) -> Dict[str, NumericSummary]:
        summary: Dict[str, NumericSummary] = {}
        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return summary
        describe_df = numeric_df.describe().transpose()
        for column, row in describe_df.iterrows():
            summary[column] = NumericSummary(
                mean=self._safe_float(row.get("mean")),
                minimum=self._safe_float(row.get("min")),
                maximum=self._safe_float(row.get("max")),
            )
        return summary

    def _build_categorical_summary(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        summary: Dict[str, List[Dict[str, Any]]] = {}
        categorical_df = df.select_dtypes(include=["object", "category"])
        for column in categorical_df.columns:
            value_counts = (
                categorical_df[column]
                .fillna("(null)")
                .value_counts(dropna=False)
                .head(self.TOP_CATEGORIES)
            )
            summary[column] = [
                {"value": str(index), "count": int(count)} for index, count in value_counts.items()
            ]
        return summary

    def _build_describe(self, df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return {}
        stats = numeric_df.describe().to_dict()
        # ensure JSON serializable floats
        cleaned: Dict[str, Dict[str, float]] = {}
        for stat_name, values in stats.items():
            cleaned[stat_name] = {
                column: self._safe_float(value) for column, value in values.items()
            }
        return cleaned

    def _build_histograms(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        histograms: Dict[str, List[Dict[str, Any]]] = {}
        numeric_df = df.select_dtypes(include=["number"])
        for column in numeric_df.columns:
            series = numeric_df[column].dropna()
            if series.empty:
                continue
            bins = min(self.TOP_CATEGORIES, max(2, series.nunique()))
            counts, bin_edges = np.histogram(series, bins=bins)
            histogram = []
            for index, count in enumerate(counts):
                left = self._safe_float(bin_edges[index])
                right = self._safe_float(bin_edges[index + 1])
                histogram.append(
                    {
                        "range": f"{left} - {right}",
                        "count": int(count),
                    }
                )
            histograms[column] = histogram
        return histograms

    def _safe_float(self, value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)
