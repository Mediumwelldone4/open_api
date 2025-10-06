import React from "react";
import { render, screen } from "@testing-library/react";

import { ConnectionsDashboard } from "./connections-dashboard";
import type { ConnectionResponse } from "./connection-wizard";

const imageStub =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg==";

describe("ConnectionsDashboard", () => {
  it("renders generated charts when visualizations are provided", () => {
    const connection: ConnectionResponse = {
      id: "conn-1",
      portal_name: "Seoul Data Portal",
      dataset_id: "traffic-speeds",
      last_ingested_at: new Date().toISOString(),
      last_ingestion_summary: {
        record_count: 5,
        schema_fields: ["value"],
        sample_records: [],
        numeric_summary: {},
        schema_details: [],
        categorical_summary: {},
        descriptive_stats: {},
        numeric_histograms: {},
        visualizations: [
          {
            column: "value",
            chart_type: "histogram",
            title: "Value Distribution",
            image_base64: imageStub,
            description: "Quick look at value spread",
          },
        ],
      },
    };

    render(
      <ConnectionsDashboard
        connections={[connection]}
        selectedId="conn-1"
        onSelect={() => {}}
        onHistoryOpen={() => {}}
      />
    );

    expect(screen.getByRole("heading", { name: /Generated charts/i })).toBeInTheDocument();
    expect(screen.getByAltText(/Value Distribution chart/i)).toBeInTheDocument();
    expect(screen.getByText(/Quick look at value spread/)).toBeInTheDocument();
  });
});
