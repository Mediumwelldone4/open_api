import React, { useMemo, useState } from "react";

import type { ConnectionResponse, IngestionSummary } from "./connection-wizard";
import { recommendPresets } from "./visualization-presets";
import { VisualizationPreview } from "./visualization-preview";
import { AiInsightsPanel } from "./ai-insights-panel";

type ConnectionsDashboardProps = {
  connections: ConnectionResponse[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onHistoryOpen: () => void;
};

const formatDateTime = (iso: string | null) => {
  if (!iso) return "-";
  const date = new Date(iso);
  return date.toLocaleString();
};

type NumericDisplay = {
  field: string;
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
  meanPercent: number | null;
};

const formatNumber = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return "-";
  return Number.isInteger(value) ? value.toString() : value.toFixed(2);
};

const summarizeNumeric = (summary: IngestionSummary | null): NumericDisplay[] => {
  if (!summary) return [];
  return Object.entries(summary.numeric_summary).map(([field, stats]) => {
    if (
      stats.minimum === null ||
      stats.maximum === null ||
      stats.mean === null ||
      stats.maximum === stats.minimum
    ) {
      return {
        field,
        mean: stats.mean,
        minimum: stats.minimum,
        maximum: stats.maximum,
        meanPercent: null,
      };
    }
    const range = stats.maximum - stats.minimum;
    const percent = ((stats.mean - stats.minimum) / range) * 100;
    return {
      field,
      mean: stats.mean,
      minimum: stats.minimum,
      maximum: stats.maximum,
      meanPercent: Math.min(100, Math.max(0, percent)),
    };
  });
};

const buildSampleRows = (summary: IngestionSummary | null) => {
  if (!summary || summary.sample_records.length === 0) {
    return { headers: [], rows: [] };
  }

  const headers = Object.keys(summary.sample_records[0]);
  const rows = summary.sample_records.slice(0, 5).map((record) =>
    headers.map((header) => {
      const value = record[header];
      if (value === null || value === undefined) return "-";
      if (value instanceof Date) return value.toISOString();
      return String(value);
    })
  );

  return { headers, rows };
};

export function ConnectionsDashboard({ connections, selectedId, onSelect, onHistoryOpen }: ConnectionsDashboardProps) {
  const [showRaw, setShowRaw] = useState(false);
  const [feedback, setFeedback] = useState("" );
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const selected = useMemo(
    () => connections.find((item) => item.id === selectedId) ?? null,
    [connections, selectedId]
  );

  const numericSummary = useMemo(() => summarizeNumeric(selected?.last_ingestion_summary ?? null), [
    selected,
  ]);
  const sampleTable = useMemo(() => buildSampleRows(selected?.last_ingestion_summary ?? null), [selected]);
  const presets = useMemo(
    () => recommendPresets(selected?.last_ingestion_summary ?? null),
    [selected]
  );

  const handleFeedbackSubmit: React.FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();
    if (!feedback.trim()) return;
    setFeedback("");
    setFeedbackSubmitted(true);
    setTimeout(() => setFeedbackSubmitted(false), 2500);
  };

  return (
    <section className="connections-panel">
      <div className="connections-list">
        <header>
          <h2>Saved Connection</h2>
          <p>Review the latest ingestion summary.</p>
        </header>
        {connections.length === 0 ? (
          <p className="muted">No connections saved yet.</p>
        ) : (
          <ul>
            {[connections[0]].map((connection) => (
              <li key={connection.id}>
                <button
                  type="button"
                  className={connection.id === selectedId ? "active" : ""}
                  onClick={() => onSelect(connection.id)}
                >
                  <span className="title">{connection.portal_name}</span>
                  <span className="subtitle">{connection.dataset_id}</span>
                  <span className="timeline">Last ingestion: {formatDateTime(connection.last_ingested_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {connections.length > 1 && (
          <button type="button" className="link-button" onClick={onHistoryOpen}>
            View Connection History
          </button>
        )}
      </div>

      <div className="connections-summary">
        {selected ? (
          <div className="summary-card">
            <header>
              <h3>{selected.portal_name}</h3>
              <p>
                Dataset ID: <code>{selected.dataset_id}</code>
              </p>
              <p>Last ingestion: {formatDateTime(selected.last_ingested_at)}</p>
            </header>

            {selected.last_ingestion_summary ? (
              <div className="summary-body">
                <p>Total records: {selected.last_ingestion_summary.record_count ?? "Unknown"}</p>
                {selected.last_ingestion_summary.schema_fields.length > 0 && (
                  <p>
                    Fields: {selected.last_ingestion_summary.schema_fields.join(", ")}
                  </p>
                )}

                {numericSummary.length > 0 && (
                  <div className="chart-block">
                    <h4>Numeric summary</h4>
                    <div className="chart-grid">
                      {numericSummary.map((item) => (
                        <div key={item.field} className="chart-row">
                          <span className="field">{item.field}</span>
                          <div className="bar-container" aria-label={`${item.field} numeric summary`}>
                            <div className="bar-track" />
                            <div className="bar-label min">{formatNumber(item.minimum)}</div>
                            <div className="bar-label max">{formatNumber(item.maximum)}</div>
                            {item.meanPercent !== null && (
                              <div
                                className="bar-marker"
                                style={{ left: `${item.meanPercent}%` }}
                              >
                                {formatNumber(item.mean)}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {sampleTable.headers.length > 0 && (
                  <div>
                    <h4>Sample data</h4>
                    <button
                      type="button"
                      className="toggle"
                      onClick={() => setShowRaw((value) => !value)}
                    >
                      {showRaw ? "View table" : "View JSON"}
                    </button>
                    <div className="table-scroll">
                      {showRaw ? (
                        <pre className="preview" data-testid="raw-sample-json">
                          {JSON.stringify(selected.last_ingestion_summary.sample_records.slice(0, 5), null, 2)}
                        </pre>
                      ) : (
                        <table>
                          <thead>
                            <tr>
                              {sampleTable.headers.map((header) => (
                                <th key={header}>{header}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sampleTable.rows.map((row, rowIndex) => (
                              <tr key={`row-${rowIndex}`}>
                                {row.map((value, cellIndex) => (
                                  <td key={`cell-${rowIndex}-${cellIndex}`}>{value}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                )}

                {presets.length > 0 && (
                  <div className="chart-block">
                    <h4>Suggested visualizations</h4>
                    <ul className="preset-list">
                      {presets.map((preset) => (
                        <li key={preset.id}>
                          <strong>{preset.label}</strong>
                          <span className="muted"> — {preset.description}</span>
                          <VisualizationPreview summary={selected.last_ingestion_summary} preset={preset} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="muted">No ingestion summary is available yet.</p>
            )}
            <form className="feedback" onSubmit={handleFeedbackSubmit}>
              <label htmlFor="feedback">Dashboard feedback</label>
              <textarea
                id="feedback"
                placeholder="Share chart ideas or improvement suggestions."
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
              />
              <button type="submit">Submit feedback</button>
              {feedbackSubmitted && <p className="success">Feedback saved. Thank you!</p>}
            </form>
            <AiInsightsPanel
              connectionId={selected.id}
              canAnalyze={Boolean(selected.last_ingestion_summary)}
            />
          </div>
        ) : (
          <div className="summary-card placeholder">
            <p>Select a connection on the left to view its summary here.</p>
          </div>
        )}
      </div>
    </section>
  );
}
