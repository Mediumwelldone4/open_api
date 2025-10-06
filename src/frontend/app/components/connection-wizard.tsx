"use client";

import React, { useMemo, useState } from "react";

import { Modal } from "./modal";
import { DataAnalysisModal } from "./data-analysis-modal";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type FormParameter = {
  name: string;
  value: string;
};

export type ConnectionTestResponse = {
  success: boolean;
  status_code: number | null;
  reason: string | null;
  content_type: string | null;
  detected_format: "json" | "xml" | "unknown";
  record_count: number | null;
  schema_fields: string[];
  preview: string | null;
  preview_truncated: boolean;
  elapsed_ms: number;
  request_url: string | null;
  error: string | null;
  raw_response: string | null;
};

export type NumericSummary = {
  mean: number | null;
  minimum: number | null;
  maximum: number | null;
};

export type VisualizationArtifact = {
  column: string;
  chart_type: string;
  title: string;
  image_base64: string;
  description?: string | null;
};

export type IngestionSummary = {
  record_count: number | null;
  schema_fields: string[];
  sample_records: Record<string, unknown>[];
  numeric_summary: Record<string, NumericSummary>;
  schema_details: { column: string; dtype: string; non_null: number; null_count: number }[];
  categorical_summary: Record<string, { value: string; count: number }[]>;
  descriptive_stats: Record<string, Record<string, number | null>>;
  numeric_histograms: Record<string, { range: string; count: number }[]>;
  visualizations?: VisualizationArtifact[];
};

export type IngestionJobResponse = {
  job_id: string;
  connection_id: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  message: string | null;
  errors: string[];
  summary: IngestionSummary | null;
};

export type ConnectionResponse = {
  id: string;
  portal_name: string;
  dataset_id: string;
  last_ingested_at: string | null;
  last_ingestion_summary: IngestionSummary | null;
};

type FormState = {
  portalName: string;
  datasetId: string;
  baseUrl: string;
  path: string;
  apiKeyName: string;
  apiKeyValue: string;
  dataFormat: "auto" | "json" | "xml";
  parameters: FormParameter[];
};

const initialParameter: FormParameter = { name: "", value: "" };

const initialState: FormState = {
  portalName: "",
  datasetId: "",
  baseUrl: "",
  path: "",
  apiKeyName: "",
  apiKeyValue: "",
  dataFormat: "auto",
  parameters: [initialParameter],
};

const prettyPreview = (response: ConnectionTestResponse | null) => {
  if (!response?.preview) {
    return null;
  }

  if (response.detected_format === "json") {
    try {
      const parsed = JSON.parse(response.preview);
      return JSON.stringify(parsed, null, 2);
    } catch (error) {
      return response.preview;
    }
  }

  return response.preview;
};

const formatJobStatus = (status: IngestionJobResponse["status"]) => {
  switch (status) {
    case "pending":
      return "Pending";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
};

const formatNumber = (value: number | null | undefined) => {
  if (value === null || value === undefined) {
    return "-";
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(2);
};

type ConnectionWizardProps = {
  onConnectionSaved?: (id: string) => void;
  onJobCompleted?: (connectionId: string, job: IngestionJobResponse) => void;
};

export function ConnectionWizard({ onConnectionSaved, onJobCompleted }: ConnectionWizardProps) {
  const [form, setForm] = useState<FormState>(initialState);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<ConnectionTestResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<IngestionJobResponse | null>(null);
  const [ingestState, setIngestState] = useState<
    "idle" | "starting" | "polling" | "completed" | "failed" | "timeout"
  >("idle");
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [showRawModal, setShowRawModal] = useState(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);

  const formattedPreview = useMemo(() => prettyPreview(result), [result]);
  const rawResponse = useMemo(() => result?.raw_response ?? result?.preview ?? "", [result]);

  const resetResult = () => {
    if (status !== "idle") {
      setStatus("idle");
    }
    if (result) {
      setResult(null);
    }
    if (errorMessage) {
      setErrorMessage(null);
    }
    if (connectionId) {
      setConnectionId(null);
    }
    if (saveState !== "idle") {
      setSaveState("idle");
    }
    if (saveError) {
      setSaveError(null);
    }
    if (jobStatus) {
      setJobStatus(null);
    }
    if (ingestState !== "idle") {
      setIngestState("idle");
    }
    if (ingestError) {
      setIngestError(null);
    }
  };

  const buildPayload = () => ({
    portal_name: form.portalName,
    dataset_id: form.datasetId,
    base_url: form.baseUrl,
    path: form.path,
    api_key_name: form.apiKeyName || null,
    api_key_value: form.apiKeyValue || null,
    data_format: form.dataFormat,
    query_parameters: form.parameters
      .filter((param) => param.name.trim() && param.value.trim())
      .map((param) => ({ name: param.name.trim(), value: param.value.trim() })),
  });

  const handleFieldChange = (field: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleParameterChange = (index: number, field: keyof FormParameter, value: string) => {
    setForm((prev) => {
      const nextParameters = prev.parameters.map((param, idx) =>
        idx === index ? { ...param, [field]: value } : param
      );
      return { ...prev, parameters: nextParameters };
    });
  };

  const addParameterRow = () => {
    setForm((prev) => ({ ...prev, parameters: [...prev.parameters, { ...initialParameter }] }));
  };

  const removeParameterRow = (index: number) => {
    setForm((prev) => ({
      ...prev,
      parameters: prev.parameters.filter((_, idx) => idx !== index),
    }));
  };

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();
    setStatus("loading");
    setErrorMessage(null);

    const payload = buildPayload();

    try {
      const response = await fetch(`${API_BASE_URL}/connections/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        setErrorMessage(errorBody.detail ?? "Connection test failed.");
        setStatus("error");
        return;
      }

      const data: ConnectionTestResponse = await response.json();
      setResult(data);
      setStatus(data.success ? "success" : "error");
      if (!data.success) {
      setErrorMessage(data.error ?? data.reason ?? "Connection test failed.");
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "An unexpected error occurred.");
      setStatus("error");
    }
  };

  const handleSaveConnection = async () => {
    const payload = buildPayload();
    setSaveState("saving");
    setSaveError(null);
    setConnectionId(null);
    setJobStatus(null);

    try {
      const response = await fetch(`${API_BASE_URL}/connections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        setSaveError(errorBody.detail ?? "Failed to save connection.");
        setSaveState("error");
        return;
      }

      const data: ConnectionResponse = await response.json();
      setConnectionId(data.id);
      setSaveState("saved");
      onConnectionSaved?.(data.id);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "An error occurred while saving.");
      setSaveState("error");
    }
  };

  const pollJobStatus = async (connectionId: string, jobId: string) => {
    setIngestState("polling");

    for (let attempt = 0; attempt < 12; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 750));
      try {
        const response = await fetch(
          `${API_BASE_URL}/connections/${connectionId}/ingest/${jobId}`
        );
        if (!response.ok) {
          setIngestError("Unable to check ingestion status.");
          setIngestState("failed");
          return;
        }

        const data: IngestionJobResponse = await response.json();
        setJobStatus(data);

        if (data.status === "completed") {
          setIngestState("completed");
          onJobCompleted?.(connectionId, data);
          return;
        }
        if (data.status === "failed") {
          setIngestError(data.message ?? "Data ingestion failed.");
          setIngestState("failed");
          onJobCompleted?.(connectionId, data);
          return;
        }
      } catch (error) {
        setIngestError("Error while checking ingestion status.");
        setIngestState("failed");
        return;
      }
    }

    setIngestError("Ingestion did not finish in the expected time.");
    setIngestState("timeout");
  };

  const handleIngestion = async () => {
    if (!connectionId) {
      setIngestError("Save the connection before running ingestion.");
      setIngestState("failed");
      return;
    }

    setIngestState("starting");
    setIngestError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/connections/${connectionId}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force_refresh: false }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        setIngestError(errorBody.detail ?? "Failed to start data ingestion.");
        setIngestState("failed");
        return;
      }

      const job: IngestionJobResponse = await response.json();
      setJobStatus(job);
      await pollJobStatus(connectionId, job.job_id);
    } catch (error) {
      setIngestError(error instanceof Error ? error.message : "An error occurred while ingesting data.");
      setIngestState("failed");
    }
  };

  return (
    <section>
      <form className="connection-form" onSubmit={handleSubmit} onChange={resetResult}>
        <div className="field-group">
          <label htmlFor="portalName">Open Data Portal</label>
          <input
            id="portalName"
            name="portalName"
            value={form.portalName}
            onChange={(event) => handleFieldChange("portalName", event.target.value)}
            placeholder="e.g. data.go.kr"
            required
          />
        </div>

        <div className="field-group">
          <label htmlFor="datasetId">Dataset ID</label>
          <input
            id="datasetId"
            name="datasetId"
            value={form.datasetId}
            onChange={(event) => handleFieldChange("datasetId", event.target.value)}
            placeholder="Dataset identifier"
            required
          />
        </div>

        <div className="field-group">
          <label htmlFor="baseUrl">API Base URL</label>
          <input
            id="baseUrl"
            name="baseUrl"
            value={form.baseUrl}
            onChange={(event) => handleFieldChange("baseUrl", event.target.value)}
            placeholder="https://"
            required
          />
        </div>

        <div className="field-group">
          <label htmlFor="path">Endpoint Path</label>
          <input
            id="path"
            name="path"
            value={form.path}
            onChange={(event) => handleFieldChange("path", event.target.value)}
            placeholder="/api/datasets"
            required
          />
        </div>

        <div className="field-inline">
          <div className="field-group">
            <label htmlFor="apiKeyName">API Key Parameter</label>
            <input
              id="apiKeyName"
              name="apiKeyName"
              value={form.apiKeyName}
              onChange={(event) => handleFieldChange("apiKeyName", event.target.value)}
              placeholder="e.g. serviceKey"
            />
          </div>
          <div className="field-group">
            <label htmlFor="apiKeyValue">API Key Value</label>
            <input
              id="apiKeyValue"
              name="apiKeyValue"
              value={form.apiKeyValue}
              onChange={(event) => handleFieldChange("apiKeyValue", event.target.value)}
              placeholder="API key value"
              type="password"
            />
          </div>
        </div>

        <fieldset className="field-group">
          <legend>Response Format</legend>
          <label>
            <input
              type="radio"
              name="dataFormat"
              value="auto"
              checked={form.dataFormat === "auto"}
              onChange={(event) =>
                handleFieldChange("dataFormat", event.target.value as FormState["dataFormat"])
              }
            />
            Auto detect
          </label>
          <label>
            <input
              type="radio"
              name="dataFormat"
              value="json"
              checked={form.dataFormat === "json"}
              onChange={(event) =>
                handleFieldChange("dataFormat", event.target.value as FormState["dataFormat"])
              }
            />
            JSON
          </label>
          <label>
            <input
              type="radio"
              name="dataFormat"
              value="xml"
              checked={form.dataFormat === "xml"}
              onChange={(event) =>
                handleFieldChange("dataFormat", event.target.value as FormState["dataFormat"])
              }
            />
            XML
          </label>
        </fieldset>

        <div className="parameters">
          <div className="parameters-header">
            <h2>Query Parameters</h2>
            <button type="button" onClick={addParameterRow}>
              + Add parameter
            </button>
          </div>
          {form.parameters.map((param, index) => (
            <div className="parameter-row" key={`param-${index}`}>
              <input
                aria-label={`Parameter name ${index + 1}`}
                value={param.name}
                onChange={(event) => handleParameterChange(index, "name", event.target.value)}
                placeholder="Parameter name"
              />
              <input
                aria-label={`Parameter value ${index + 1}`}
                value={param.value}
                onChange={(event) => handleParameterChange(index, "value", event.target.value)}
                placeholder="Parameter value"
              />
              {form.parameters.length > 1 && (
                <button type="button" onClick={() => removeParameterRow(index)}>
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>

        <button className="submit" type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Testing..." : "Test Connection"}
        </button>
      </form>

      {status !== "idle" && (
        <div className="results">
          {status === "error" && errorMessage && <p className="error">{errorMessage}</p>}
          {result && (
            <div className="result-grid">
              <div>
                <h3>Response summary</h3>
                <ul>
                  <li>HTTP Status: {result.status_code ?? "N/A"}</li>
                  <li>Elapsed: {result.elapsed_ms}ms</li>
                  <li>Detected Format: {result.detected_format}</li>
                  <li>Content-Type: {result.content_type ?? "N/A"}</li>
                  <li>Record Count: {result.record_count ?? "Unknown"}</li>
                </ul>
                {result.schema_fields.length > 0 && (
                  <div>
                    <h4>Fields</h4>
                    <p>{result.schema_fields.join(", ")}</p>
                  </div>
                )}
                {status === "success" && (
                  <p className="info" data-testid="connection-success">Request completed successfully.</p>
                )}
                <button
                  type="button"
                  className="link-button"
                  onClick={() => setShowRawModal(true)}
                >
                  View Raw Response
                </button>
              </div>
              <div>
                <h3>Data Preview</h3>
                {formattedPreview ? (
                  <pre className="preview" data-testid="data-preview">
                    {formattedPreview}
                  </pre>
                ) : (
                  <p>No preview available.</p>
                )}
                {result.preview_truncated && <p>Preview truncated to 4,000 characters.</p>}
              </div>
            </div>
          )}

          {status === "success" && (
            <div className="actions">
              <button
                type="button"
                onClick={handleSaveConnection}
                disabled={saveState === "saving"}
              >
                {saveState === "saving" ? "Saving..." : "Save Connection"}
              </button>
              <button
                type="button"
                onClick={handleIngestion}
                disabled={!connectionId || ingestState === "starting" || ingestState === "polling"}
              >
                {ingestState === "starting" || ingestState === "polling"
                  ? "Fetching data..."
                  : "Run Data Ingestion"}
              </button>
            </div>
          )}

          {saveState === "saved" && connectionId && (
            <p className="info">New connection ID: {connectionId}</p>
          )}
          {saveState === "error" && saveError && <p className="error">{saveError}</p>}

          {ingestError && <p className="error">{ingestError}</p>}

          {jobStatus && (
            <div className="job-summary">
              <h3>
                Ingestion Status: <span className={`pill ${jobStatus.status}`}>{formatJobStatus(jobStatus.status)}</span>
              </h3>
              {jobStatus.message && <p>{jobStatus.message}</p>}
              {jobStatus.summary && (
                <div className="job-details">
                  <p>Total records: {jobStatus.summary.record_count ?? "Unknown"}</p>
                  {jobStatus.summary.schema_fields.length > 0 && (
                    <p>Fields: {jobStatus.summary.schema_fields.join(", ")}</p>
                  )}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setShowAnalysisModal(true)}
                  >
                    View Analysis
                  </button>
                  {Object.keys(jobStatus.summary.numeric_summary).length > 0 && (
                    <div>
                      <h4>Numeric summary</h4>
                      <table className="numeric-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Mean</th>
                            <th>Min</th>
                            <th>Max</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(jobStatus.summary.numeric_summary).map(
                            ([field, summary]) => (
                              <tr key={field}>
                                <td>{field}</td>
                                <td>{formatNumber(summary.mean)}</td>
                                <td>{formatNumber(summary.minimum)}</td>
                                <td>{formatNumber(summary.maximum)}</td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {jobStatus.summary.sample_records.length > 0 && (
                    <div>
                      <h4>Sample records</h4>
                      <pre className="preview" data-testid="ingestion-sample">
                        {JSON.stringify(jobStatus.summary.sample_records[0], null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
      <Modal open={showRawModal} onClose={() => setShowRawModal(false)} title="Raw Data">
        {rawResponse ? (
          <pre className="preview modal-preview" data-testid="raw-response">
            {rawResponse}
          </pre>
        ) : (
          <p className="muted">Raw response is empty.</p>
        )}
      </Modal>
      <DataAnalysisModal
        open={showAnalysisModal}
        onClose={() => setShowAnalysisModal(false)}
        summary={jobStatus?.summary ?? null}
      />
    </section>
  );
}
