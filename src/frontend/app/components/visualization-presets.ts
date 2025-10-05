import type { IngestionSummary, NumericSummary } from "./connection-wizard";

export type VisualizationPresetType = "numeric" | "categorical" | "timeseries";

export type VisualizationPreset = {
  id: string;
  label: string;
  description: string;
  fields: string[];
  type: VisualizationPresetType;
};

const createNumericPreset = (
  field: string,
  summary: NumericSummary
): VisualizationPreset => ({
  id: `numeric-${field}`,
  label: `${field} distribution`,
  description: "Visualize the numeric distribution using histogram or line chart.",
  fields: [field],
  type: "numeric",
});

const createCategoricalPreset = (fields: string[]): VisualizationPreset => ({
  id: `categorical-${fields.join("-")}`,
  label: "Category frequency",
  description: "Create a bar chart showing the most common categorical values.",
  fields,
  type: "categorical",
});

const createTimeSeriesPreset = (field: string): VisualizationPreset => ({
  id: `timeseries-${field}`,
  label: `${field} time series`,
  description: "Plot the time-based trend for the selected field.",
  fields: [field],
  type: "timeseries",
});

const isLikelyTimestamp = (value: unknown): boolean => {
  if (typeof value !== "string") return false;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed);
};

const collectTimestampFields = (summary: IngestionSummary): string[] => {
  const record = summary.sample_records[0];
  if (!record) return [];
  return Object.entries(record)
    .filter(([, value]) => isLikelyTimestamp(value))
    .map(([key]) => key);
};

const collectCategoricalFields = (summary: IngestionSummary): string[] => {
  const record = summary.sample_records[0];
  if (!record) return [];
  return Object.entries(record)
    .filter(([, value]) => typeof value === "string" && !isLikelyTimestamp(value))
    .map(([key]) => key);
};

export const recommendPresets = (summary: IngestionSummary | null): VisualizationPreset[] => {
  if (!summary) return [];

  const presets: VisualizationPreset[] = [];

  Object.entries(summary.numeric_summary).forEach(([field, stats]) => {
    presets.push(createNumericPreset(field, stats));
  });

  const categorical = collectCategoricalFields(summary).slice(0, 2);
  if (categorical.length > 0) {
    presets.push(createCategoricalPreset(categorical));
  }

  const temporal = collectTimestampFields(summary);
  temporal.forEach((field) => {
    presets.push(createTimeSeriesPreset(field));
  });

  return presets;
};
