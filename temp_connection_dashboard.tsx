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
          <h2>저장된 연결</h2>
          <p>TEMP_TOKEN_최근 수집 시각과 요약을 확인하세요.</p>
        </header>
        {connections.length === 0 ? (
          <p className="muted">아직 저장된 연결이 없습니다.</p>
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
                  <span className="timeline">TEMP_TOKEN_최근 수집: {formatDateTime(connection.last_ingested_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {connections.length > 1 && (
          <button type="button" className="link-button" onClick={onHistoryOpen}>
            연결 히스토리 보기
          </button>
        )}
      </div>

      <div className="connections-summary">
        {selected ? (
          <div className="summary-card">
            <header>
              <h3>{selected.portal_name}</h3>
              <p>
                TEMP_TOKEN_TEMP_TOKEN_데이터셋 ID: <code>{selected.dataset_id}</code>
              </p>
              <p>TEMP_TOKEN_최근 수집: {formatDateTime(selected.last_ingested_at)}</p>
            </header>

            {selected.last_ingestion_summary ? (
              <div className="summary-body">
                <p>TEMP_TOKEN_총 레코드 수: {selected.last_ingestion_summary.record_count ?? "알 수 없음"}</p>
                {selected.last_ingestion_summary.schema_fields.length > 0 && (
                  <p>
                    TEMP_TOKEN_필드: {selected.last_ingestion_summary.schema_fields.join(", ")}
                  </p>
                )}

                {numericSummary.length > 0 && (
                  <div className="chart-block">
                    <h4>TEMP_TOKEN_숫자 통계</h4>
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
                    <h4>TEMP_TOKEN_샘플 TEMP_TOKEN_데이터</h4>
                    <button
                      type="button"
                      className="toggle"
                      onClick={() => setShowRaw((value) => !value)}
                    >
                      {showRaw ? "TEMP_TOKEN_원본 테이블 보기" : "JSON 원문 보기"}
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
                    <h4>추천 시각화</h4>
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
              <p className="muted">아직 수집된 TEMP_TOKEN_데이터 요약이 없습니다.</p>
            )}
            <form className="feedback" onSubmit={handleFeedbackSubmit}>
              <label htmlFor="feedback">대시보드 개선 의견</label>
              <textarea
                id="feedback"
                placeholder="차트 제안이나 개선 아이디어를 남겨주세요."
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
              />
              <button type="submit">피드백 남기기</button>
              {feedbackSubmitted && <p className="success">의견이 기록되었습니다. 감사합니다!</p>}
            </form>
            <AiInsightsPanel
              connectionId={selected.id}
              canAnalyze={Boolean(selected.last_ingestion_summary)}
            />
          </div>
        ) : (
          <div className="summary-card placeholder">
            <p>왼쪽에서 연결을 선택하면 여기에서 요약을 볼 수 있습니다.</p>
          </div>
        )}
      </div>
    </section>
  );
}
