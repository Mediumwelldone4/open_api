from __future__ import annotations

import base64
import io
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import seaborn as sns

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .models import IngestionSummary, NumericSummary, VisualizationArtifact


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
        visualizations = self._build_visualizations(df)

        return IngestionSummary(
            record_count=int(len(df)),
            schema_fields=schema_fields,
            schema_details=schema_details,
            sample_records=sample_records,
            numeric_summary=numeric_summary,
            categorical_summary=categorical_summary,
            descriptive_stats=descriptive_stats,
            numeric_histograms=numeric_histograms,
            visualizations=visualizations,
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

    def _build_visualizations(self, df: pd.DataFrame) -> List[VisualizationArtifact]:
        visualizations: List[VisualizationArtifact] = []
        if df.empty:
            return visualizations

        sns.set_theme(style="whitegrid")

        for column in df.columns:
            series = df[column].dropna()
            if series.empty:
                continue

            try:
                if pd.api.types.is_numeric_dtype(series):
                    artifact = self._visualize_numeric(column, series)
                elif pd.api.types.is_datetime64_any_dtype(series) or self._looks_like_datetime(series):
                    artifact = self._visualize_datetime(column, series)
                else:
                    artifact = self._visualize_categorical(column, series)
            except Exception:
                continue

            if artifact:
                visualizations.append(artifact)

        return visualizations

    def _encode_figure(self, fig: plt.Figure) -> str:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("ascii")
        plt.close(fig)
        return encoded

    def _visualize_numeric(self, column: str, series: pd.Series) -> VisualizationArtifact:
        fig, ax = plt.subplots(figsize=(4, 3))
        bins = min(30, max(5, series.nunique()))
        sns.histplot(series, bins=bins, kde=False, ax=ax, color="#2563eb")
        ax.set_title(f"{column} distribution")
        ax.set_xlabel(column)
        ax.set_ylabel("Frequency")
        encoded = self._encode_figure(fig)
        description = "Frequency distribution of continuous numeric values"
        return VisualizationArtifact(
            column=column,
            chart_type="histogram",
            title=f"{column} Distribution",
            image_base64=encoded,
            description=description,
        )

    def _visualize_categorical(self, column: str, series: pd.Series) -> VisualizationArtifact | None:
        value_counts = (
            series.astype("string")
            .replace({pd.NA: "(null)"})
            .value_counts(dropna=False)
            .head(self.TOP_CATEGORIES)
        )
        if value_counts.empty:
            return None

        fig, ax = plt.subplots(figsize=(4, 3))
        sns.barplot(x=value_counts.values, y=value_counts.index, ax=ax, color="#2563eb")
        ax.set_title(f"Top {self.TOP_CATEGORIES} values for {column}")
        ax.set_xlabel("Frequency")
        ax.set_ylabel(column)
        encoded = self._encode_figure(fig)
        description = "Top category value frequencies"
        return VisualizationArtifact(
            column=column,
            chart_type="bar",
            title=f"Top values for {column}",
            image_base64=encoded,
            description=description,
        )

    def _visualize_datetime(self, column: str, series: pd.Series) -> VisualizationArtifact | None:
        datetime_series = pd.to_datetime(series, errors="coerce").dropna()
        if datetime_series.empty:
            return None

        grouped = datetime_series.dt.to_period("D").value_counts().sort_index()
        if grouped.empty:
            return None

        fig, ax = plt.subplots(figsize=(4, 3))
        grouped.index = grouped.index.to_timestamp()
        sns.lineplot(x=grouped.index, y=grouped.values, ax=ax, marker="o", color="#2563eb")
        ax.set_title(f"{column} trend")
        ax.set_xlabel("Date")
        ax.set_ylabel("Frequency")
        fig.autofmt_xdate()
        encoded = self._encode_figure(fig)
        description = "Daily occurrence trend for datetime field"
        return VisualizationArtifact(
            column=column,
            chart_type="line",
            title=f"{column} Trend",
            image_base64=encoded,
            description=description,
        )

    def _looks_like_datetime(self, series: pd.Series) -> bool:
        if series.empty:
            return False
        sample = series.astype("string").head(20)
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        return parsed.notna().sum() >= max(3, len(sample) // 2)
