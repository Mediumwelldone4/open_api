"use client";

import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import type { IngestionSummary } from "./connection-wizard";
import { Modal } from "./modal";

function renderNumericTable(summary: IngestionSummary) {
  const entries = Object.entries(summary.numeric_summary ?? {});
  if (entries.length === 0) {
    return <p className="muted">No numeric columns detected.</p>;
  }
  return (
    <table className="analysis-table">
      <thead>
        <tr>
          <th>Field</th>
          <th>Mean</th>
          <th>Min</th>
          <th>Max</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([field, stats]) => (
          <tr key={field}>
            <td>{field}</td>
            <td>{stats.mean ?? "-"}</td>
            <td>{stats.minimum ?? "-"}</td>
            <td>{stats.maximum ?? "-"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderCategorical(summary: IngestionSummary) {
  const entries = Object.entries(summary.categorical_summary ?? {});
  if (entries.length === 0) {
    return <p className="muted">No categorical columns detected.</p>;
  }
  return (
    <div className="categorical-grid">
      {entries.map(([field, values]) => (
        <div key={field} className="categorical-card">
          <h4>{field}</h4>
          <ul>
            {values.map((item) => (
              <li key={`${field}-${item.value}`}>
                <span>{item.value}</span>
                <span>{item.count.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function renderSchemaDetails(summary: IngestionSummary) {
  if (!summary.schema_details || summary.schema_details.length === 0) {
    return <p className="muted">Schema information unavailable.</p>;
  }
  return (
    <table className="analysis-table">
      <thead>
        <tr>
          <th>Field</th>
          <th>Data type</th>
          <th>Null count</th>
          <th>Non-null</th>
        </tr>
      </thead>
      <tbody>
        {summary.schema_details.map((detail) => (
          <tr key={detail.column}>
            <td>{detail.column}</td>
            <td>{detail.dtype}</td>
            <td>{detail.null_count}</td>
            <td>{detail.non_null}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderSamples(summary: IngestionSummary) {
  if (!summary.sample_records || summary.sample_records.length === 0) {
    return <p className="muted">No sample records available.</p>;
  }
  const columns = Object.keys(summary.sample_records[0] ?? {});
  return (
    <div className="table-scroll analysis-samples">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={`sample-${column}`}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {summary.sample_records.map((record, rowIndex) => (
            <tr key={`sample-row-${rowIndex}`}>
              {columns.map((column) => (
                <td key={`sample-cell-${rowIndex}-${column}`}>
                  {String(record[column] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderDescriptive(summary: IngestionSummary) {
  const entries = Object.entries(summary.descriptive_stats ?? {});
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="analysis-describe">
      {entries.map(([stat, values]) => (
        <div key={stat}>
          <h4>{stat}</h4>
          <ul>
            {Object.entries(values).map(([column, value]) => (
              <li key={`${stat}-${column}`}>
                <span>{column}</span>
                <span>{value ?? "-"}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

type Props = {
  open: boolean;
  onClose: () => void;
  summary: IngestionSummary | null;
};

function renderHistogramCharts(summary: IngestionSummary) {
  const entries = Object.entries(summary.numeric_histograms ?? {});
  if (entries.length === 0) {
    return <p className="muted">No numeric columns available for histograms.</p>;
  }
  return (
    <div className="chart-grid">
      {entries.map(([field, histogram]) => (
        <div key={`hist-${field}`} className="chart-card">
          <h4>{field} distribution</h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={histogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
              <XAxis dataKey="range" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} stroke="rgba(148,163,184,0.8)" />
              <Tooltip />
              <Bar dataKey="count" fill="#38bdf8" radius={[4, 4, 4, 4]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}

function renderCategoricalCharts(summary: IngestionSummary) {
  const entries = Object.entries(summary.categorical_summary ?? {});
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="chart-grid">
      {entries.map(([field, values]) => (
        <div key={`cat-chart-${field}`} className="chart-card">
          <h4>{field} top {values.length} values</h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={values} layout="vertical" margin={{ left: 60, top: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
              <XAxis type="number" stroke="rgba(148,163,184,0.8)" allowDecimals={false} />
              <YAxis dataKey="value" type="category" width={120} stroke="rgba(148,163,184,0.8)" />
              <Tooltip />
              <Bar dataKey="count" fill="#f97316" radius={[4, 4, 4, 4]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}

function renderGeneratedVisuals(summary: IngestionSummary) {
  const visualizations = summary.visualizations ?? [];
  if (visualizations.length === 0) {
    return <p className="muted">No generated charts available.</p>;
  }
  return (
    <div className="visualization-gallery">
      {visualizations.map((artifact, index) => (
        <figure
          key={`${artifact.column}-${artifact.chart_type}-${index}`}
          className="visualization-card"
        >
          <img
            src={`data:image/png;base64,${artifact.image_base64}`}
            alt={`${artifact.title} chart for ${artifact.column}`}
            loading="lazy"
          />
          <figcaption>
            <strong>{artifact.title}</strong>
            <span className="muted visualization-meta">
              {artifact.chart_type}
              {artifact.column ? ` • ${artifact.column}` : ""}
            </span>
            {artifact.description && <p>{artifact.description}</p>}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export function DataAnalysisModal({ open, onClose, summary }: Props) {
  return (
    <Modal open={open} onClose={onClose} title="Dataset Analysis">
      {summary ? (
        <div className="analysis-grid">
          <section>
            <h4>Summary</h4>
            <p>Total records: {summary.record_count ?? "Unknown"}</p>
          </section>
          <section>
            <h4>Schema</h4>
            {renderSchemaDetails(summary)}
          </section>
          <section>
            <h4>Numeric summary</h4>
            {renderNumericTable(summary)}
          </section>
          <section>
            <h4>Numeric distributions (histograms)</h4>
            {renderHistogramCharts(summary)}
          </section>
          <section>
            <h4>Categorical summary</h4>
            {renderCategorical(summary)}
          </section>
          <section>
            <h4>Categorical distributions</h4>
            {renderCategoricalCharts(summary) ?? <p className="muted">No categorical distribution data.</p>}
          </section>
          <section>
            <h4>Generated charts</h4>
            {renderGeneratedVisuals(summary)}
          </section>
          <section>
            <h4>Descriptive statistics</h4>
            {renderDescriptive(summary) ?? <p className="muted">No additional statistics available.</p>}
          </section>
          <section>
            <h4>Sample records</h4>
            {renderSamples(summary)}
          </section>
        </div>
      ) : (
        <p className="muted">No ingested data to analyze yet.</p>
      )}
    </Modal>
  );
}
