"use client";

import React, { useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type AiInsightsPanelProps = {
  connectionId: string | null;
  canAnalyze: boolean;
};

export function AiInsightsPanel({ connectionId, canAnalyze }: AiInsightsPanelProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("" );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();
    if (!connectionId || !question.trim()) {
      setError("Please enter a question before submitting.");
      return;
    }
    setLoading(true);
    setError(null);
    setAnswer("");

    try {
      const response = await fetch(`${API_BASE_URL}/connections/${connectionId}/analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        setError(body.detail ?? "Failed to request AI analysis.");
        return;
      }
      const data = await response.json();
      setAnswer(data.answer ?? "");
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="ai-panel">
      <h3>AI Insights</h3>
      <form onSubmit={handleSubmit} className="ai-form">
        <label htmlFor="aiQuestion">Question</label>
        <textarea
          id="aiQuestion"
          placeholder="Ask something about your dataset."
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={!canAnalyze || loading}
        />
        <button type="submit" disabled={!canAnalyze || loading}>
          {loading ? "Requesting..." : "Request Analysis"}
        </button>
        {!canAnalyze && <p className="muted">Run data ingestion before requesting insights.</p>}
        {error && <p className="error">{error}</p>}
      </form>
      {answer && (
        <article className="ai-answer" data-testid="ai-answer">
          <h4>Response</h4>
          <p>{answer}</p>
        </article>
      )}
    </section>
  );
}
