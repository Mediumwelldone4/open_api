"use client";

import React, { useMemo, useState } from "react";

import type { ConnectionResponse } from "./connection-wizard";
import { Modal } from "./modal";

function filterConnections(connections: ConnectionResponse[], filterText: string) {
  if (!filterText.trim()) return connections;
  const keyword = filterText.toLowerCase();
  return connections.filter((connection) => {
    return (
      connection.portal_name.toLowerCase().includes(keyword) ||
      connection.dataset_id.toLowerCase().includes(keyword)
    );
  });
}

type Props = {
  open: boolean;
  onClose: () => void;
  connections: ConnectionResponse[];
  onSelect: (id: string) => void;
};

export function HistoryModal({ open, onClose, connections, onSelect }: Props) {
  const [filterText, setFilterText] = useState("");
  const filtered = useMemo(
    () => filterConnections(connections.slice(1), filterText),
    [connections, filterText]
  );

  const handleSelect = (id: string) => {
    onSelect(id);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Connection History">
      {connections.length <= 1 ? (
        <p className="muted">No previous connections found.</p>
      ) : (
        <div className="history-modal">
          <div className="history-filter">
            <label htmlFor="history-filter-input">Search</label>
            <input
              id="history-filter-input"
              placeholder="Portal or dataset name"
              value={filterText}
              onChange={(event) => setFilterText(event.target.value)}
            />
          </div>
          <div className="history-list">
            {filtered.length === 0 ? (
              <p className="muted">No matching connections.</p>
            ) : (
              <ul>
                {filtered.map((connection) => (
                  <li key={connection.id}>
                    <button type="button" onClick={() => handleSelect(connection.id)}>
                      <span className="title">{connection.portal_name}</span>
                      <span className="subtitle">{connection.dataset_id}</span>
                      <span className="timeline">
                        Last ingestion: {connection.last_ingested_at ?? "Not ingested"}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
