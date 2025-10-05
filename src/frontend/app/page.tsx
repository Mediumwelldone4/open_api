'use client';

import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  ConnectionWizard,
  type ConnectionResponse,
  type IngestionJobResponse,
} from "./components/connection-wizard";
import { ConnectionsDashboard } from "./components/connections-dashboard";
import { HistoryModal } from "./components/history-modal";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ConnectionListResponse = {
  items: ConnectionResponse[];
  count: number;
};

export default function HomePage() {
  const [connections, setConnections] = useState<ConnectionResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  const fetchConnections = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE_URL}/connections`);
      if (!response.ok) {
        throw new Error("Failed to retrieve saved connections.");
      }
      const data: ConnectionListResponse = await response.json();
      setConnections(data.items);
      if (data.items.length > 0 && !data.items.find((item) => item.id === selectedId)) {
        setSelectedId(data.items[0].id);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Error while loading saved connections.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleConnectionSaved = useCallback(
    (id: string) => {
      setSelectedId(id);
      fetchConnections();
    },
    [fetchConnections]
  );

  const handleJobCompleted = useCallback(
    (connectionId: string, _job: IngestionJobResponse) => {
      setSelectedId(connectionId);
      fetchConnections();
    },
    [fetchConnections]
  );

  const dashboardConnections = useMemo(() => connections, [connections]);

  return (
    <main>
      <h1>Open Data Insight Platform</h1>
      <p className="intro">
        Test open data APIs, save connections, run ingestion, and explore automatic summaries in one place.
      </p>
      <div className="layout-grid">
        <ConnectionWizard
          onConnectionSaved={handleConnectionSaved}
          onJobCompleted={handleJobCompleted}
        />
        <ConnectionsDashboard
          connections={dashboardConnections}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onHistoryOpen={() => setShowHistory(true)}
        />
      </div>
      {isLoading && <p className="muted">Loading saved connections...</p>}
      {errorMessage && <p className="error">{errorMessage}</p>}
      <HistoryModal
        open={showHistory}
        onClose={() => setShowHistory(false)}
        connections={connections}
        onSelect={(id) => {
          setSelectedId(id);
          setShowHistory(false);
        }}
      />
    </main>
  );
}
